"""
Schemas de Processo, Prazo e Andamento.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.models.processo import (
    FaseProcessual,
    StatusPrazo,
    TipoBeneficio,
    TipoPrazo,
)
from app.schemas.base import BaseSchema, IDMixin, TimestampMixin


# ==================== PRAZO ====================

class PrazoBase(BaseSchema):
    """Campos base do prazo."""
    
    tipo: TipoPrazo
    descricao: str = Field(..., min_length=5, max_length=500)
    data_fatal: date
    data_inicio: date | None = None
    dias_prazo: int | None = None
    observacoes: str | None = None


class PrazoCreate(PrazoBase):
    """Schema para criação de prazo."""
    
    processo_id: UUID


class PrazoUpdate(BaseSchema):
    """Schema para atualização de prazo."""
    
    descricao: str | None = None
    data_fatal: date | None = None
    status: StatusPrazo | None = None
    observacoes: str | None = None


class PrazoResponse(PrazoBase, IDMixin, TimestampMixin):
    """Schema de resposta do prazo."""
    
    processo_id: UUID
    status: StatusPrazo
    data_cumprimento: datetime | None
    notificacao_enviada: bool
    dias_restantes: int
    is_urgente: bool
    is_vencido: bool


class PrazoPendente(BaseSchema):
    """Schema para listagem de prazos pendentes."""
    
    id: UUID
    tipo: TipoPrazo
    descricao: str
    data_fatal: date
    dias_restantes: int
    is_urgente: bool
    processo_numero: str
    cliente_nome: str


# ==================== ANDAMENTO ====================

class AndamentoBase(BaseSchema):
    """Campos base do andamento."""
    
    data: datetime
    descricao: str = Field(..., min_length=10)
    fonte: str | None = None
    gera_prazo: bool = False


class AndamentoCreate(AndamentoBase):
    """Schema para criação de andamento."""
    
    processo_id: UUID


class AndamentoResponse(AndamentoBase, IDMixin, TimestampMixin):
    """Schema de resposta do andamento."""
    
    processo_id: UUID
    is_public: bool
    registrado_por_id: UUID | None


# ==================== PROCESSO ====================

class ProcessoBase(BaseSchema):
    """Campos base do processo."""
    
    numero_cnj: str | None = Field(
        None,
        pattern=r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$",
        description="Formato: NNNNNNN-DD.AAAA.J.TR.OOOO",
    )
    numero_administrativo: str | None = None
    tipo_beneficio: TipoBeneficio
    
    # Localização
    tribunal: str | None = None
    vara: str | None = None
    comarca: str | None = None
    agencia_inss: str | None = None
    
    # Datas
    data_entrada: date
    data_distribuicao: date | None = None
    
    # Valores
    valor_causa: float | None = None
    
    # Descrição
    objeto: str | None = None
    observacoes: str | None = None


class ProcessoCreate(ProcessoBase):
    """Schema para criação de processo."""
    
    cliente_id: UUID
    advogado_responsavel_id: UUID | None = None


class ProcessoUpdate(BaseSchema):
    """Schema para atualização de processo."""
    
    numero_cnj: str | None = None
    fase: FaseProcessual | None = None
    tribunal: str | None = None
    vara: str | None = None
    comarca: str | None = None
    
    data_citacao: date | None = None
    data_sentenca: date | None = None
    data_transito: date | None = None
    
    valor_causa: float | None = None
    valor_condenacao: float | None = None
    
    objeto: str | None = None
    observacoes: str | None = None
    resultado: str | None = None
    
    advogado_responsavel_id: UUID | None = None
    is_archived: bool | None = None


class ProcessoResponse(ProcessoBase, IDMixin, TimestampMixin):
    """Schema de resposta completa do processo."""
    
    escritorio_id: UUID
    cliente_id: UUID
    advogado_responsavel_id: UUID | None
    
    fase: FaseProcessual
    is_active: bool
    is_archived: bool
    resultado: str | None
    
    data_citacao: date | None
    data_sentenca: date | None
    data_transito: date | None
    valor_condenacao: float | None
    
    numero_principal: str
    
    # Relacionamentos inline
    prazos: list[PrazoResponse] = []
    andamentos: list[AndamentoResponse] = []


class ProcessoListResponse(BaseSchema):
    """Schema simplificado para listagem de processos."""
    
    id: UUID
    numero_principal: str
    tipo_beneficio: TipoBeneficio
    fase: FaseProcessual
    cliente_nome: str
    data_entrada: date
    proximo_prazo: PrazoResponse | None = None
    is_archived: bool


class ProcessoStats(BaseSchema):
    """Estatísticas de processos."""
    
    total: int
    por_fase: dict[str, int]
    por_tipo_beneficio: dict[str, int]
    prazos_pendentes: int
    prazos_urgentes: int
