"""
Modelo do Escritório de Advocacia.

Este é o tenant principal do sistema - todas as entidades
pertencem a um escritório específico.
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Escritorio(Base):
    """Escritório de advocacia (tenant principal)."""
    
    __tablename__ = "escritorios"
    
    # Dados básicos
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    razao_social: Mapped[str | None] = mapped_column(String(255))
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True)
    oab_sociedade: Mapped[str | None] = mapped_column(String(20))
    
    # Contato
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    telefone: Mapped[str | None] = mapped_column(String(20))
    
    # Endereço
    endereco: Mapped[str | None] = mapped_column(Text)
    cidade: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str | None] = mapped_column(String(2))
    cep: Mapped[str | None] = mapped_column(String(10))
    
    # Configurações
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Logo e configurações visuais (path no GCS)
    logo_path: Mapped[str | None] = mapped_column(String(500))
    
    # Relacionamentos
    usuarios: Mapped[list["Usuario"]] = relationship(  # noqa: F821
        "Usuario",
        back_populates="escritorio",
        lazy="selectin",
    )
    
    clientes: Mapped[list["Cliente"]] = relationship(  # noqa: F821
        "Cliente",
        back_populates="escritorio",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Escritorio(id={self.id}, nome='{self.nome}')>"
