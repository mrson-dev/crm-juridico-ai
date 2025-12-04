"""
Base class para todos os modelos SQLAlchemy.

Define campos comuns e configurações padrão.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Type

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


def PgEnum(enum_class: Type) -> SQLEnum:
    """
    Cria um SQLAlchemy Enum que usa os valores (values) em vez dos nomes (names).
    
    Isso é necessário para compatibilidade com PostgreSQL que espera valores
    em minúsculo no banco, enquanto Python Enums usam nomes em maiúsculo.
    
    Exemplo:
        class UserRole(str, enum.Enum):
            ADMIN = "admin"  # Nome: ADMIN, Valor: admin
        
        # Sem PgEnum: PostgreSQL recebe "ADMIN" (falha)
        # Com PgEnum: PostgreSQL recebe "admin" (funciona)
    """
    return SQLEnum(enum_class, values_callable=lambda x: [e.value for e in x])


class Base(DeclarativeBase):
    """
    Classe base para todos os modelos.
    
    Inclui campos padrão: id, created_at, updated_at
    """
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    
    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Gera nome da tabela automaticamente a partir do nome da classe."""
        # CamelCase -> snake_case
        name = cls.__name__
        return "".join(
            ["_" + c.lower() if c.isupper() else c for c in name]
        ).lstrip("_")

    def to_dict(self) -> dict[str, Any]:
        """Converte modelo para dicionário."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class MultiTenantBase(Base):
    """
    Base para modelos com multi-tenancy.
    
    Todos os modelos que herdam desta classe terão isolamento por escritório.
    """
    
    __abstract__ = True
    
    escritorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("escritorios.id"),
        nullable=False,
        index=True,
    )
