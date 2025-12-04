"""
Dependências injetáveis do FastAPI.

Define dependências reutilizáveis para autenticação, database session,
e serviços compartilhados.
"""

from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    InsufficientPermissionsError,
    ResourceNotFoundError,
)
from app.core.security import verify_token
from app.db.session import async_session_maker
from app.models.usuario import Usuario, UserRole
from app.repositories.usuario_repository import UsuarioRepository

security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency que fornece uma sessão de banco de dados.
    
    Uso:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user_firebase(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """
    Dependency que valida token Firebase e retorna usuário do banco.
    
    Fluxo:
    1. Valida token Firebase
    2. Extrai firebase_uid
    3. Busca usuário no banco local pelo firebase_uid
    
    Raises:
        HTTPException 401: Token inválido ou usuário não encontrado
    """
    from app.core.firebase_auth import firebase_auth_service
    
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Valida token Firebase
        firebase_data = await firebase_auth_service.verify_token(credentials.credentials)
        firebase_uid = firebase_data.get("uid")
        
        if not firebase_uid:
            raise AuthenticationError("Token inválido: UID não encontrado")
        
        # Busca usuário no banco local
        repo = UsuarioRepository(db)
        user = await repo.get_by_firebase_uid(firebase_uid)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado no sistema",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário inativo",
            )
        
        return user
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """
    Dependency que retorna o usuário autenticado.
    
    Suporta tanto JWT local quanto Firebase token.
    Em produção, use Firebase. Em desenvolvimento, pode usar JWT local.
    
    Raises:
        HTTPException 401: Token inválido ou usuário não encontrado
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Tenta primeiro como JWT local (desenvolvimento)
    payload = verify_token(credentials.credentials)
    
    if payload is not None:
        user_id = payload.get("sub")
        if user_id:
            repo = UsuarioRepository(db)
            user = await repo.get_by_id(user_id)
            
            if user and user.is_active:
                return user
    
    # Se falhou JWT local, tenta Firebase (produção)
    if settings.ENVIRONMENT != "development":
        return await get_current_user_firebase(credentials, db)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
    """Alias para get_current_user com verificação de ativo."""
    return current_user


def require_roles(*roles: UserRole):
    """
    Factory para criar dependency que exige roles específicos.
    
    Uso:
        @router.post("", dependencies=[Depends(require_roles(UserRole.ADMIN))])
        async def create_item(...):
            ...
    """
    async def role_checker(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if current_user.role not in roles:
            raise InsufficientPermissionsError(
                f"Requer role: {', '.join(r.value for r in roles)}"
            )
        return current_user
    
    return role_checker


async def get_escritorio_id(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> UUID:
    """Retorna o escritorio_id do usuário autenticado."""
    return current_user.escritorio_id


# Type aliases para facilitar uso nas rotas
DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[Usuario, Depends(get_current_user)]
EscritorioID = Annotated[UUID, Depends(get_escritorio_id)]

# Role-based dependencies
AdminUser = Annotated[Usuario, Depends(require_roles(UserRole.ADMIN))]
AdvogadoUser = Annotated[Usuario, Depends(require_roles(UserRole.ADMIN, UserRole.ADVOGADO))]
