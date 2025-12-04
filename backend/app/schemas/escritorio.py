"""
Schemas do Escritório.
"""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema, IDMixin, TimestampMixin


class EscritorioBase(BaseSchema):
    """Campos base do escritório."""
    
    nome: str = Field(..., min_length=2, max_length=255)
    razao_social: str | None = None
    cnpj: str | None = Field(None, pattern=r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")
    oab_sociedade: str | None = None
    
    # Contato
    email: EmailStr
    telefone: str | None = None
    
    # Endereço
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = Field(None, max_length=2)
    cep: str | None = Field(None, pattern=r"^\d{5}-?\d{3}$")


class EscritorioCreate(EscritorioBase):
    """Schema para criação de escritório."""
    pass


class EscritorioUpdate(BaseSchema):
    """Schema para atualização parcial de escritório."""
    
    nome: str | None = Field(None, min_length=2, max_length=255)
    razao_social: str | None = None
    oab_sociedade: str | None = None
    email: EmailStr | None = None
    telefone: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = Field(None, max_length=2)
    cep: str | None = None
    is_active: bool | None = None


class EscritorioResponse(EscritorioBase, IDMixin, TimestampMixin):
    """Schema de resposta do escritório."""
    
    is_active: bool
    logo_path: str | None = None


class EscritorioListResponse(BaseSchema):
    """Schema simplificado para listagem."""
    
    id: UUID
    nome: str
    cnpj: str | None
    email: str
    is_active: bool
