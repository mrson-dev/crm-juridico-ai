"""
Schemas de Honorários e Financeiro.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.honorario import (
    FormaPagamento,
    StatusContrato,
    StatusParcela,
    TipoHonorario,
)
from app.schemas.base import BaseSchema, IDMixin, TimestampMixin


# ==================== PARCELA ====================

class ParcelaBase(BaseSchema):
    """Campos base da parcela."""
    
    numero_parcela: int = Field(..., ge=1)
    descricao: str | None = None
    valor: Decimal = Field(..., gt=0)
    data_vencimento: date


class ParcelaCreate(ParcelaBase):
    """Schema para criação de parcela."""
    pass


class ParcelaUpdate(BaseSchema):
    """Schema para atualização de parcela."""
    
    descricao: str | None = None
    valor: Decimal | None = Field(None, gt=0)
    data_vencimento: date | None = None


class ParcelaRegistrarPagamento(BaseSchema):
    """Schema para registrar pagamento de parcela."""
    
    valor_pago: Decimal = Field(..., gt=0)
    data_pagamento: date
    forma_pagamento: FormaPagamento
    observacoes: str | None = None


class ParcelaResponse(ParcelaBase, IDMixin, TimestampMixin):
    """Schema de resposta da parcela."""
    
    contrato_id: UUID
    valor_pago: Decimal | None
    data_pagamento: date | None
    status: StatusParcela
    forma_pagamento: FormaPagamento | None
    comprovante_path: str | None
    
    is_atrasada: bool
    dias_atraso: int


class ParcelaListResponse(BaseSchema):
    """Schema simplificado para listagem."""
    
    id: UUID
    numero_parcela: int
    valor: Decimal
    data_vencimento: date
    status: StatusParcela
    is_atrasada: bool
    dias_atraso: int


# ==================== CONTRATO ====================

class ContratoBase(BaseSchema):
    """Campos base do contrato de honorários."""
    
    tipo: TipoHonorario
    valor_total: Decimal = Field(..., gt=0)
    
    # Para tipos específicos
    valor_entrada: Decimal | None = Field(None, ge=0)
    percentual_exito: Decimal | None = Field(None, ge=0, le=100)
    valor_hora: Decimal | None = Field(None, gt=0)
    
    # Parcelamento
    numero_parcelas: int = Field(1, ge=1)
    dia_vencimento: int | None = Field(None, ge=1, le=31)
    
    # Datas
    data_inicio: date
    data_fim: date | None = None
    
    # Descrição
    descricao_servicos: str | None = None
    observacoes: str | None = None


class ContratoCreate(ContratoBase):
    """Schema para criação de contrato."""
    
    cliente_id: UUID
    processo_id: UUID | None = None
    advogado_responsavel_id: UUID
    
    # Se True, gera parcelas automaticamente
    gerar_parcelas: bool = True


class ContratoUpdate(BaseSchema):
    """Schema para atualização de contrato."""
    
    status: StatusContrato | None = None
    valor_total: Decimal | None = Field(None, gt=0)
    data_assinatura: date | None = None
    data_fim: date | None = None
    descricao_servicos: str | None = None
    observacoes: str | None = None


class ContratoResponse(ContratoBase, IDMixin, TimestampMixin):
    """Schema de resposta do contrato."""
    
    escritorio_id: UUID
    cliente_id: UUID
    processo_id: UUID | None
    advogado_responsavel_id: UUID
    
    status: StatusContrato
    data_assinatura: date | None
    documento_path: str | None
    
    # Calculados
    valor_pago: Decimal
    valor_pendente: Decimal
    percentual_pago: float
    
    # Parcelas inline
    parcelas: list[ParcelaResponse] = []


class ContratoListResponse(BaseSchema):
    """Schema simplificado para listagem."""
    
    id: UUID
    tipo: TipoHonorario
    status: StatusContrato
    valor_total: Decimal
    valor_pago: Decimal
    percentual_pago: float
    cliente_nome: str
    data_inicio: date
    proxima_parcela: ParcelaListResponse | None = None


class ContratoStats(BaseSchema):
    """Estatísticas financeiras."""
    
    total_contratos: int
    valor_total_contratado: Decimal
    valor_total_recebido: Decimal
    valor_total_pendente: Decimal
    
    parcelas_atrasadas: int
    valor_atrasado: Decimal
    
    por_tipo: dict[str, int]
    por_status: dict[str, int]


# ==================== DASHBOARD FINANCEIRO ====================

class DashboardFinanceiro(BaseSchema):
    """Dados para dashboard financeiro."""
    
    # Resumo geral
    receita_mes_atual: Decimal
    receita_mes_anterior: Decimal
    variacao_percentual: float
    
    # Previsão
    previsao_mes_atual: Decimal
    recebido_mes_atual: Decimal
    
    # Inadimplência
    total_atrasado: Decimal
    parcelas_atrasadas: int
    
    # Próximos recebimentos
    proximos_vencimentos: list[ParcelaListResponse]
    
    # Gráfico mensal (últimos 12 meses)
    historico_mensal: list[dict]


class ResumoFinanceiro(BaseSchema):
    """Resumo financeiro simplificado."""
    
    total_contratado: Decimal
    total_pago: Decimal
    total_pendente: Decimal
    percentual_pago: float
