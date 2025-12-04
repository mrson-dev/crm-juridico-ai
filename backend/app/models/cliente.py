"""
Modelo do Cliente.

Em direito previdenciário, o cliente geralmente é pessoa física
buscando benefícios junto ao INSS.
"""

import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import MultiTenantBase, PgEnum


class TipoPessoa(str, enum.Enum):
    """Tipo de pessoa."""
    
    FISICA = "fisica"
    JURIDICA = "juridica"


class EstadoCivil(str, enum.Enum):
    """Estado civil do cliente."""
    
    SOLTEIRO = "solteiro"
    CASADO = "casado"
    DIVORCIADO = "divorciado"
    VIUVO = "viuvo"
    UNIAO_ESTAVEL = "uniao_estavel"


class Cliente(MultiTenantBase):
    """
    Cliente do escritório.
    
    Contém dados pessoais, documentos e informações relevantes
    para processos previdenciários.
    """
    
    __tablename__ = "clientes"
    
    # Tipo de pessoa
    tipo_pessoa: Mapped[TipoPessoa] = mapped_column(
        PgEnum(TipoPessoa),
        default=TipoPessoa.FISICA,
        nullable=False,
    )
    
    # Dados de identificação
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cpf: Mapped[str | None] = mapped_column(String(14), index=True)
    rg: Mapped[str | None] = mapped_column(String(20))
    rg_orgao_emissor: Mapped[str | None] = mapped_column(String(20))
    rg_data_emissao: Mapped[date | None] = mapped_column(Date)
    
    # Para pessoa jurídica
    cnpj: Mapped[str | None] = mapped_column(String(18))
    razao_social: Mapped[str | None] = mapped_column(String(255))
    
    # Dados pessoais
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    sexo: Mapped[str | None] = mapped_column(String(1))  # M/F
    estado_civil: Mapped[EstadoCivil | None] = mapped_column(PgEnum(EstadoCivil))
    profissao: Mapped[str | None] = mapped_column(String(100))
    nacionalidade: Mapped[str | None] = mapped_column(String(50), default="Brasileira")
    naturalidade: Mapped[str | None] = mapped_column(String(100))
    
    # Filiação
    nome_mae: Mapped[str | None] = mapped_column(String(255))
    nome_pai: Mapped[str | None] = mapped_column(String(255))
    
    # Contato
    email: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    telefone_secundario: Mapped[str | None] = mapped_column(String(20))
    
    # Endereço
    cep: Mapped[str | None] = mapped_column(String(10))
    logradouro: Mapped[str | None] = mapped_column(String(255))
    numero: Mapped[str | None] = mapped_column(String(20))
    complemento: Mapped[str | None] = mapped_column(String(100))
    bairro: Mapped[str | None] = mapped_column(String(100))
    cidade: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str | None] = mapped_column(String(2))
    
    # Dados previdenciários
    nit_pis_pasep: Mapped[str | None] = mapped_column(String(20))
    ctps_numero: Mapped[str | None] = mapped_column(String(20))
    ctps_serie: Mapped[str | None] = mapped_column(String(10))
    ctps_estado: Mapped[str | None] = mapped_column(String(2))
    
    # Dados bancários (para recebimento de benefícios)
    banco: Mapped[str | None] = mapped_column(String(100))
    agencia: Mapped[str | None] = mapped_column(String(20))
    conta: Mapped[str | None] = mapped_column(String(30))
    tipo_conta: Mapped[str | None] = mapped_column(String(20))  # corrente/poupanca
    
    # Observações
    observacoes: Mapped[str | None] = mapped_column(Text)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # LGPD
    consentimento_lgpd: Mapped[bool] = mapped_column(Boolean, default=False)
    data_consentimento: Mapped[date | None] = mapped_column(Date)
    
    # Relacionamentos
    escritorio: Mapped["Escritorio"] = relationship(  # noqa: F821
        "Escritorio",
        back_populates="clientes",
    )
    
    processos: Mapped[list["Processo"]] = relationship(  # noqa: F821
        "Processo",
        back_populates="cliente",
        lazy="selectin",
    )
    
    documentos: Mapped[list["Documento"]] = relationship(  # noqa: F821
        "Documento",
        back_populates="cliente",
        lazy="selectin",
    )
    
    @property
    def documento_principal(self) -> str | None:
        """Retorna CPF ou CNPJ conforme tipo de pessoa."""
        if self.tipo_pessoa == TipoPessoa.FISICA:
            return self.cpf
        return self.cnpj
    
    @property
    def idade(self) -> int | None:
        """Calcula idade atual do cliente."""
        if not self.data_nascimento:
            return None
        today = date.today()
        return (
            today.year
            - self.data_nascimento.year
            - (
                (today.month, today.day)
                < (self.data_nascimento.month, self.data_nascimento.day)
            )
        )
    
    def __repr__(self) -> str:
        return f"<Cliente(id={self.id}, nome='{self.nome}', cpf='{self.cpf}')>"
