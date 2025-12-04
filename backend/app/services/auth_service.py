"""
Service de Autenticação.

Gerencia login local e integração com Firebase Auth.
"""

from datetime import timedelta
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    FirebaseAuthError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
)
from app.core.firebase_auth import firebase_auth_service
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.models.usuario import Usuario, UserRole
from app.repositories.escritorio_repository import EscritorioRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario import (
    LoginResponse,
    UsuarioCreate,
    UsuarioCreateFirebase,
    UsuarioResponse,
)

logger = structlog.get_logger()


class AuthService:
    """
    Service de autenticação.
    
    Suporta autenticação local (JWT) e Firebase Auth.
    """
    
    def __init__(self, db: AsyncSession):
        self._db = db
        self._usuario_repo = UsuarioRepository(db)
    
    async def create_escritorio_with_admin(
        self,
        escritorio_nome: str,
        escritorio_email: str,
        usuario_nome: str,
        usuario_email: str,
        usuario_password: str,
        escritorio_cnpj: str | None = None,
        escritorio_telefone: str | None = None,
        usuario_oab_numero: str | None = None,
        usuario_oab_estado: str | None = None,
    ) -> dict:
        """
        Cria escritório e usuário admin em uma única transação.
        
        Usado no onboarding de novos clientes.
        """
        from app.models.escritorio import Escritorio
        from app.models.usuario import Usuario, UserRole
        
        # Verificar se email do usuário já existe
        existing_user = await self._usuario_repo.get_by_email(usuario_email)
        if existing_user:
            raise ResourceAlreadyExistsError("Usuario", "email", usuario_email)
        
        # Verificar se CNPJ do escritório já existe
        if escritorio_cnpj:
            escritorio_repo = EscritorioRepository(self._db)
            existing_esc = await escritorio_repo.get_by_cnpj(escritorio_cnpj)
            if existing_esc:
                raise ResourceAlreadyExistsError("Escritorio", "cnpj", escritorio_cnpj)
        
        # Criar escritório
        escritorio = Escritorio(
            nome=escritorio_nome,
            cnpj=escritorio_cnpj,
            email=escritorio_email,
            telefone=escritorio_telefone,
        )
        self._db.add(escritorio)
        await self._db.flush()  # Para obter o ID
        
        # Criar usuário admin
        usuario = Usuario(
            email=usuario_email,
            nome=usuario_nome,
            hashed_password=get_password_hash(usuario_password),
            escritorio_id=escritorio.id,
            role=UserRole.ADMIN,
            oab_numero=usuario_oab_numero,
            oab_estado=usuario_oab_estado,
            is_active=True,
        )
        self._db.add(usuario)
        await self._db.commit()
        await self._db.refresh(escritorio)
        await self._db.refresh(usuario)
        
        # Gerar token de acesso
        access_token = create_access_token(
            subject=str(usuario.id),
            additional_claims={
                "escritorio_id": str(escritorio.id),
                "role": usuario.role.value,
            },
        )
        
        logger.info(
            "Onboarding concluído",
            escritorio_id=str(escritorio.id),
            usuario_id=str(usuario.id),
        )
        
        return {
            "escritorio_id": escritorio.id,
            "usuario_id": usuario.id,
            "access_token": access_token,
        }
    
    async def login_local(self, email: str, password: str) -> dict:
        """
        Login com email/senha (desenvolvimento).
        
        Em produção, usar Firebase Auth.
        """
        user = await self._usuario_repo.get_by_email(email)
        
        if not user:
            logger.warning("Login falhou: usuário não encontrado", email=email)
            raise AuthenticationError("Email ou senha inválidos")
        
        if not user.hashed_password:
            raise AuthenticationError("Usuário não possui senha local. Use Firebase.")
        
        if not verify_password(password, user.hashed_password):
            logger.warning("Login falhou: senha inválida", email=email)
            raise AuthenticationError("Email ou senha inválidos")
        
        if not user.is_active:
            raise AuthenticationError("Usuário inativo")
        
        # Gera token JWT
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={
                "escritorio_id": str(user.escritorio_id),
                "role": user.role.value,
            },
        )
        
        logger.info("Login realizado com sucesso", user_id=str(user.id))
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "usuario": user,
        }
    
    async def login_firebase(self, id_token: str) -> LoginResponse:
        """
        Login via Firebase ID Token.
        
        Valida token Firebase e retorna JWT local ou dados do usuário.
        """
        # Valida token Firebase
        firebase_data = await firebase_auth_service.verify_token(id_token)
        firebase_uid = firebase_data.get("uid")
        email = firebase_data.get("email")
        
        # Busca usuário no banco local
        user = await self._usuario_repo.get_by_firebase_uid(firebase_uid)
        
        if not user:
            logger.warning(
                "Login Firebase: usuário não encontrado no sistema",
                firebase_uid=firebase_uid,
                email=email,
            )
            raise AuthenticationError(
                "Usuário não cadastrado no sistema. Entre em contato com o administrador."
            )
        
        if not user.is_active:
            raise AuthenticationError("Usuário inativo")
        
        # Gera token JWT local (opcional - pode usar apenas Firebase token)
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={
                "escritorio_id": str(user.escritorio_id),
                "role": user.role.value,
                "firebase_uid": firebase_uid,
            },
        )
        
        logger.info("Login Firebase realizado", user_id=str(user.id))
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UsuarioResponse.model_validate(user),
        )
    
    async def register_user(
        self,
        dados: UsuarioCreate,
        admin_user: Usuario | None = None,
    ) -> Usuario:
        """
        Registra novo usuário (com senha local).
        
        Usado principalmente em desenvolvimento.
        """
        # Verifica se email já existe
        existing = await self._usuario_repo.get_by_email(dados.email)
        if existing:
            raise ResourceAlreadyExistsError("Usuario", "email", dados.email)
        
        # Verifica se escritório existe
        escritorio_repo = EscritorioRepository(self._db)
        escritorio = await escritorio_repo.get_by_id(dados.escritorio_id)
        if not escritorio:
            raise ResourceNotFoundError("Escritorio", dados.escritorio_id)
        
        # Cria usuário
        user_data = dados.model_dump(exclude={"password"})
        user_data["hashed_password"] = get_password_hash(dados.password)
        
        user = await self._usuario_repo.create(**user_data)
        
        logger.info(
            "Usuário registrado",
            user_id=str(user.id),
            email=user.email,
            created_by=str(admin_user.id) if admin_user else "self",
        )
        
        return user
    
    async def register_user_firebase(
        self,
        dados: UsuarioCreateFirebase,
        admin_user: Usuario | None = None,
    ) -> Usuario:
        """
        Registra usuário que já existe no Firebase.
        
        Usado quando o usuário já se cadastrou no Firebase e precisa
        ser vinculado ao sistema.
        """
        # Verifica se firebase_uid já existe
        existing = await self._usuario_repo.get_by_firebase_uid(dados.firebase_uid)
        if existing:
            raise ResourceAlreadyExistsError("Usuario", "firebase_uid", dados.firebase_uid)
        
        # Verifica se email já existe
        existing_email = await self._usuario_repo.get_by_email(dados.email)
        if existing_email:
            raise ResourceAlreadyExistsError("Usuario", "email", dados.email)
        
        # Verifica se escritório existe
        escritorio_repo = EscritorioRepository(self._db)
        escritorio = await escritorio_repo.get_by_id(dados.escritorio_id)
        if not escritorio:
            raise ResourceNotFoundError("Escritorio", dados.escritorio_id)
        
        # Cria usuário
        user = await self._usuario_repo.create(**dados.model_dump())
        
        # Define custom claims no Firebase para o frontend
        try:
            await firebase_auth_service.set_custom_claims(
                dados.firebase_uid,
                {
                    "crm_user_id": str(user.id),
                    "escritorio_id": str(user.escritorio_id),
                    "role": user.role.value,
                },
            )
        except FirebaseAuthError as e:
            logger.warning("Erro ao definir custom claims no Firebase", error=str(e))
        
        logger.info(
            "Usuário Firebase registrado",
            user_id=str(user.id),
            firebase_uid=dados.firebase_uid,
        )
        
        return user
    
    async def change_password(
        self,
        user: Usuario,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Altera senha do usuário (apenas autenticação local)."""
        if not user.hashed_password:
            raise AuthenticationError("Usuário não possui senha local")
        
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Senha atual incorreta")
        
        await self._usuario_repo.update(
            user.id,
            hashed_password=get_password_hash(new_password),
        )
        
        logger.info("Senha alterada", user_id=str(user.id))
        return True
    
    async def request_password_reset(self, email: str) -> str | None:
        """
        Solicita reset de senha.
        
        Para Firebase, gera link de reset.
        Para local, poderia enviar email (não implementado).
        """
        user = await self._usuario_repo.get_by_email(email)
        
        if not user:
            # Não revela se email existe ou não
            logger.info("Reset de senha solicitado para email não cadastrado", email=email)
            return None
        
        if user.firebase_uid:
            # Usa Firebase para reset
            reset_link = await firebase_auth_service.send_password_reset_email(email)
            logger.info("Link de reset Firebase gerado", user_id=str(user.id))
            return reset_link
        
        # Reset local não implementado
        logger.warning("Reset de senha local não implementado")
        return None
