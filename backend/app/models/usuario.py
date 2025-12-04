"""
Modelo do Usuário do sistema.
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PgEnum


class UserRole(str, enum.Enum):
    """Papéis de usuário no sistema."""
    
    ADMIN = "admin"  # Administrador do escritório
    ADVOGADO = "advogado"  # Advogado com OAB
    ESTAGIARIO = "estagiario"  # Estagiário
    SECRETARIA = "secretaria"  # Secretária/Administrativo
    FINANCEIRO = "financeiro"  # Acesso apenas a financeiro


class Usuario(Base):
    """Usuário do sistema CRM."""
    
    __tablename__ = "usuarios"
    
    # Firebase Authentication
    firebase_uid: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        index=True,
        comment="UID do Firebase Authentication",
    )
    
    # Dados de autenticação (backup local / desenvolvimento)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    
    # Dados pessoais
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(14), unique=True)
    telefone: Mapped[str | None] = mapped_column(String(20))
    
    # Avatar (path no GCS)
    avatar_path: Mapped[str | None] = mapped_column(String(500))
    
    # Dados profissionais (para advogados)
    oab_numero: Mapped[str | None] = mapped_column(String(20))
    oab_estado: Mapped[str | None] = mapped_column(String(2))
    
    # Controle de acesso
    role: Mapped[UserRole] = mapped_column(
        PgEnum(UserRole),
        default=UserRole.ADVOGADO,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Preferências do usuário (JSON)
    preferences: Mapped[str | None] = mapped_column(
        Text,
        comment="JSON com preferências do usuário",
    )
    
    # Relacionamento com escritório
    escritorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("escritorios.id"),
        nullable=False,
        index=True,
    )
    
    escritorio: Mapped["Escritorio"] = relationship(  # noqa: F821
        "Escritorio",
        back_populates="usuarios",
    )
    
    @property
    def oab_completa(self) -> str | None:
        """Retorna OAB no formato UF123456."""
        if self.oab_numero and self.oab_estado:
            return f"{self.oab_estado}{self.oab_numero}"
        return None
    
    @property
    def is_advogado(self) -> bool:
        """Verifica se usuário é advogado."""
        return self.role in (UserRole.ADMIN, UserRole.ADVOGADO)
    
    def __repr__(self) -> str:
        return f"<Usuario(id={self.id}, email='{self.email}', role={self.role.value})>"
