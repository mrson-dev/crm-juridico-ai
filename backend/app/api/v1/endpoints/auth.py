"""
Endpoints de Autenticação.

Rotas para login, registro e gerenciamento de usuários.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    CurrentUser,
    DBSession,
    EscritorioID,
    get_current_user,
)
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
)
from app.schemas.base import APIResponse
from app.schemas.usuario import (
    FirebaseLoginRequest,
    LoginRequest,
    LoginResponse,
    UsuarioCreate,
    UsuarioCreateFirebase,
    UsuarioResponse,
    UsuarioUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


# === Schemas de Onboarding ===

class OnboardingRequest(BaseModel):
    """Schema para criar escritório + usuário admin."""
    
    # Dados do escritório
    escritorio_nome: str = Field(..., min_length=2, max_length=255)
    escritorio_cnpj: str | None = Field(None, pattern=r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")
    escritorio_email: EmailStr
    escritorio_telefone: str | None = None
    
    # Dados do usuário admin
    usuario_nome: str = Field(..., min_length=2, max_length=255)
    usuario_email: EmailStr
    usuario_password: str = Field(..., min_length=8)
    usuario_oab_numero: str | None = None
    usuario_oab_estado: str | None = Field(None, max_length=2)


class OnboardingResponse(BaseModel):
    """Resposta do onboarding."""
    
    escritorio_id: str
    usuario_id: str
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(
    request: LoginRequest,
    db: DBSession,
):
    """
    Login com email e senha.
    
    Retorna token JWT para autenticação nas demais rotas.
    """
    try:
        service = AuthService(db)
        result = await service.login_local(request.email, request.password)
        
        return APIResponse(
            success=True,
            data=LoginResponse(
                access_token=result["access_token"],
                token_type=result["token_type"],
                expires_in=result.get("expires_in", 86400),
                user=UsuarioResponse.model_validate(result["usuario"]),
            ),
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/onboarding", response_model=APIResponse[OnboardingResponse])
async def onboarding(
    request: OnboardingRequest,
    db: DBSession,
):
    """
    Cria novo escritório e usuário administrador.
    
    Endpoint para onboarding de novos clientes do sistema.
    Cria o escritório e o primeiro usuário (admin) em uma única operação.
    """
    try:
        service = AuthService(db)
        result = await service.create_escritorio_with_admin(
            escritorio_nome=request.escritorio_nome,
            escritorio_cnpj=request.escritorio_cnpj,
            escritorio_email=request.escritorio_email,
            escritorio_telefone=request.escritorio_telefone,
            usuario_nome=request.usuario_nome,
            usuario_email=request.usuario_email,
            usuario_password=request.usuario_password,
            usuario_oab_numero=request.usuario_oab_numero,
            usuario_oab_estado=request.usuario_oab_estado,
        )
        
        return APIResponse(
            success=True,
            data=OnboardingResponse(
                escritorio_id=str(result["escritorio_id"]),
                usuario_id=str(result["usuario_id"]),
                access_token=result["access_token"],
                token_type="bearer",
            ),
            message="Escritório e usuário criados com sucesso",
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login/firebase", response_model=APIResponse[LoginResponse])
async def login_firebase(
    request: FirebaseLoginRequest,
    db: DBSession,
):
    """
    Login com token Firebase.
    
    Valida token Firebase e retorna JWT interno + dados do usuário.
    """
    try:
        service = AuthService(db)
        result = await service.login_firebase(request.firebase_token)
        
        return APIResponse(
            success=True,
            data=LoginResponse(
                access_token=result["access_token"],
                token_type=result["token_type"],
                usuario=UsuarioResponse.model_validate(result["usuario"]),
            ),
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=APIResponse[UsuarioResponse])
async def register(
    request: UsuarioCreate,
    db: DBSession,
):
    """
    Registra novo usuário com email e senha.
    
    Requer escritorio_id válido.
    """
    try:
        service = AuthService(db)
        usuario = await service.register_user(request)
        
        return APIResponse(
            success=True,
            data=UsuarioResponse.model_validate(usuario),
            message="Usuário registrado com sucesso",
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/register/firebase", response_model=APIResponse[UsuarioResponse])
async def register_firebase(
    request: UsuarioCreateFirebase,
    db: DBSession,
):
    """
    Registra usuário Firebase no sistema.
    
    Sincroniza dados do Firebase Auth com o banco local.
    """
    try:
        service = AuthService(db)
        usuario = await service.register_user_firebase(request)
        
        return APIResponse(
            success=True,
            data=UsuarioResponse.model_validate(usuario),
            message="Usuário registrado com sucesso",
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/me", response_model=APIResponse[UsuarioResponse])
async def get_current_user_info(
    current_user: CurrentUser,
):
    """Retorna dados do usuário autenticado."""
    return APIResponse(
        success=True,
        data=UsuarioResponse.model_validate(current_user),
    )


@router.put("/me", response_model=APIResponse[UsuarioResponse])
async def update_current_user(
    dados: UsuarioUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Atualiza dados do usuário autenticado."""
    from app.repositories.usuario_repository import UsuarioRepository
    
    repo = UsuarioRepository(db, current_user.escritorio_id)
    usuario = await repo.update(
        current_user.id,
        **dados.model_dump(exclude_unset=True),
    )
    
    return APIResponse(
        success=True,
        data=UsuarioResponse.model_validate(usuario),
    )


@router.post("/change-password", response_model=APIResponse)
async def change_password(
    current_password: str,
    new_password: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Altera senha do usuário autenticado."""
    try:
        service = AuthService(db)
        await service.change_password(
            current_user.id,
            current_password,
            new_password,
        )
        
        return APIResponse(
            success=True,
            message="Senha alterada com sucesso",
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/forgot-password", response_model=APIResponse)
async def forgot_password(
    email: str,
    db: DBSession,
):
    """
    Solicita reset de senha.
    
    Envia email com link para redefinição (Firebase ou local).
    """
    service = AuthService(db)
    await service.request_password_reset(email)
    
    return APIResponse(
        success=True,
        message="Se o email existir, um link de recuperação será enviado",
    )
