"""
Schemas do Cliente.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.cliente import EstadoCivil, TipoPessoa
from app.schemas.base import BaseSchema, IDMixin, TimestampMixin


class ClienteBase(BaseSchema):
    """Campos base do cliente."""
    
    tipo_pessoa: TipoPessoa = TipoPessoa.FISICA
    nome: str = Field(..., min_length=2, max_length=255)
    
    # Documentos
    cpf: str | None = Field(None, pattern=r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")
    rg: str | None = None
    rg_orgao_emissor: str | None = None
    rg_data_emissao: date | None = None
    cnpj: str | None = Field(None, pattern=r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")
    razao_social: str | None = None
    
    # Dados pessoais
    data_nascimento: date | None = None
    sexo: str | None = Field(None, pattern=r"^[MF]$")
    estado_civil: EstadoCivil | None = None
    profissao: str | None = None
    nacionalidade: str | None = "Brasileira"
    naturalidade: str | None = None
    nome_mae: str | None = None
    nome_pai: str | None = None
    
    # Contato
    email: EmailStr | None = None
    telefone: str | None = None
    telefone_secundario: str | None = None
    
    # Endereço
    cep: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = Field(None, max_length=2)
    
    # Dados previdenciários
    nit_pis_pasep: str | None = None
    ctps_numero: str | None = None
    ctps_serie: str | None = None
    ctps_estado: str | None = None
    
    # Dados bancários
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    tipo_conta: str | None = None
    
    observacoes: str | None = None
    
    @field_validator("cpf", mode="before")
    @classmethod
    def validate_cpf(cls, v: str | None) -> str | None:
        """Valida CPF (validação básica de formato)."""
        if v is None:
            return v
        # Remove caracteres não numéricos para validação
        numbers = "".join(filter(str.isdigit, v))
        if len(numbers) != 11:
            raise ValueError("CPF deve conter 11 dígitos")
        return v


class ClienteCreate(ClienteBase):
    """Schema para criação de cliente."""
    
    consentimento_lgpd: bool = Field(
        ...,
        description="Cliente deve consentir com LGPD",
    )


class ClienteUpdate(BaseSchema):
    """Schema para atualização parcial de cliente."""
    
    nome: str | None = None
    email: EmailStr | None = None
    telefone: str | None = None
    telefone_secundario: str | None = None
    
    # Endereço
    cep: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    
    # Dados previdenciários
    nit_pis_pasep: str | None = None
    
    # Dados bancários
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    tipo_conta: str | None = None
    
    observacoes: str | None = None
    is_active: bool | None = None


class ClienteResponse(ClienteBase, IDMixin, TimestampMixin):
    """Schema de resposta do cliente."""
    
    escritorio_id: UUID
    is_active: bool
    consentimento_lgpd: bool
    data_consentimento: date | None
    idade: int | None = None


class ClienteListResponse(BaseSchema):
    """Schema simplificado para listagem."""
    
    id: UUID
    nome: str
    cpf: str | None
    email: str | None
    telefone: str | None
    is_active: bool
    created_at: datetime


class ClienteFromDocumentAI(BaseModel):
    """
    Dados do cliente extraídos de documento por IA.
    
    Usado quando a IA extrai dados de RG, CNH, etc.
    """
    
    nome: str | None = None
    cpf: str | None = None
    rg: str | None = None
    rg_orgao_emissor: str | None = None
    rg_data_emissao: date | None = None
    data_nascimento: date | None = None
    sexo: str | None = None
    nome_mae: str | None = None
    nome_pai: str | None = None
    naturalidade: str | None = None
    
    # Campos adicionais de CNH
    cnh_numero: str | None = None
    cnh_categoria: str | None = None
    cnh_validade: date | None = None
    
    # Confiança da extração (0-1)
    confidence: float = Field(default=0.0, ge=0, le=1)
    
    # Campos que precisam revisão manual
    fields_to_review: list[str] = Field(default_factory=list)
