"""
Schemas base compartilhados.
"""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Schema base com configurações padrão."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TimestampMixin(BaseModel):
    """Mixin com campos de timestamp."""
    
    created_at: datetime
    updated_at: datetime


class IDMixin(BaseModel):
    """Mixin com campo ID."""
    
    id: UUID


class APIResponse(BaseModel, Generic[T]):
    """
    Resposta padronizada da API.
    
    Exemplo de uso:
        return APIResponse(success=True, data=cliente)
    """
    
    success: bool
    data: T | None = None
    message: str | None = None


class ErrorDetail(BaseModel):
    """Detalhes de erro."""
    
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    """Resposta de erro padronizada."""
    
    success: bool = False
    error: ErrorDetail


class PaginatedResponse(BaseModel, Generic[T]):
    """Resposta paginada."""
    
    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
    
    @property
    def pages(self) -> int:
        """Calcula número total de páginas."""
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size
