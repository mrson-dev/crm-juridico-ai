"""
Schemas do Usuário.
"""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.models.usuario import UserRole
from app.schemas.base import BaseSchema, IDMixin, TimestampMixin


class UsuarioBase(BaseSchema):
    """Campos base do usuário."""
    
    email: EmailStr
    nome: str = Field(..., min_length=2, max_length=255)
    cpf: str | None = Field(None, pattern=r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")
    telefone: str | None = None
    
    # Dados profissionais
    oab_numero: str | None = None
    oab_estado: str | None = Field(None, max_length=2)
    
    # Controle
    role: UserRole = UserRole.ADVOGADO


class UsuarioCreate(UsuarioBase):
    """Schema para criação de usuário."""
    
    password: str = Field(..., min_length=8, description="Senha do usuário")
    escritorio_id: UUID


class UsuarioCreateFirebase(BaseSchema):
    """Schema para criação de usuário via Firebase."""
    
    firebase_uid: str = Field(..., description="UID do Firebase")
    email: EmailStr
    nome: str = Field(..., min_length=2, max_length=255)
    escritorio_id: UUID
    role: UserRole = UserRole.ADVOGADO
    
    # Opcionais
    cpf: str | None = None
    telefone: str | None = None
    oab_numero: str | None = None
    oab_estado: str | None = None


class UsuarioUpdate(BaseSchema):
    """Schema para atualização parcial de usuário."""
    
    nome: str | None = Field(None, min_length=2, max_length=255)
    telefone: str | None = None
    oab_numero: str | None = None
    oab_estado: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UsuarioUpdatePassword(BaseSchema):
    """Schema para atualização de senha."""
    
    current_password: str
    new_password: str = Field(..., min_length=8)


class UsuarioResponse(UsuarioBase, IDMixin, TimestampMixin):
    """Schema de resposta do usuário."""
    
    escritorio_id: UUID
    is_active: bool
    is_superuser: bool
    avatar_path: str | None = None
    oab_completa: str | None = None


class UsuarioListResponse(BaseSchema):
    """Schema simplificado para listagem."""
    
    id: UUID
    email: str
    nome: str
    role: UserRole
    oab_completa: str | None = None
    is_active: bool


class UsuarioMe(UsuarioResponse):
    """Schema para dados do usuário logado."""
    
    escritorio_nome: str | None = None
    permissions: list[str] = []


# === Schemas de Autenticação ===

class LoginRequest(BaseSchema):
    """Schema de login (desenvolvimento)."""
    
    email: EmailStr
    password: str


class LoginResponse(BaseSchema):
    """Schema de resposta de login."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UsuarioResponse


class FirebaseLoginRequest(BaseSchema):
    """Schema para login via Firebase."""
    
    id_token: str = Field(..., description="Token ID do Firebase")


class RefreshTokenRequest(BaseSchema):
    """Schema para refresh de token."""
    
    refresh_token: str
