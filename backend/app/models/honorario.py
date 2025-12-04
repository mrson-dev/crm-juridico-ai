"""
Modelos de Honorários e Financeiro.

Gerencia contratos de honorários, parcelas e pagamentos.
"""

import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import MultiTenantBase, PgEnum


class TipoHonorario(str, enum.Enum):
    """Tipos de cobrança de honorários."""
    
    FIXO = "fixo"  # Valor fixo único
    PARCELADO = "parcelado"  # Valor fixo parcelado
    EXITO = "exito"  # Percentual sobre êxito
    MISTO = "misto"  # Entrada + êxito
    HORA = "hora"  # Por hora trabalhada


class StatusContrato(str, enum.Enum):
    """Status do contrato de honorários."""
    
    RASCUNHO = "rascunho"
    ATIVO = "ativo"
    SUSPENSO = "suspenso"
    CANCELADO = "cancelado"
    CONCLUIDO = "concluido"


class StatusParcela(str, enum.Enum):
    """Status da parcela de pagamento."""
    
    PENDENTE = "pendente"
    PAGO = "pago"
    ATRASADO = "atrasado"
    CANCELADO = "cancelado"


class FormaPagamento(str, enum.Enum):
    """Formas de pagamento aceitas."""
    
    DINHEIRO = "dinheiro"
    PIX = "pix"
    TRANSFERENCIA = "transferencia"
    CARTAO_CREDITO = "cartao_credito"
    CARTAO_DEBITO = "cartao_debito"
    BOLETO = "boleto"
    CHEQUE = "cheque"


class ContratoHonorario(MultiTenantBase):
    """
    Contrato de honorários advocatícios.
    
    Define os termos financeiros do relacionamento com o cliente.
    """
    
    __tablename__ = "contratos_honorario"
    
    # Vinculações
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clientes.id"),
        nullable=False,
        index=True,
    )
    
    processo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processos.id"),
        index=True,
        comment="Processo específico (se aplicável)",
    )
    
    advogado_responsavel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=False,
    )
    
    # Tipo e status
    tipo: Mapped[TipoHonorario] = mapped_column(
        PgEnum(TipoHonorario),
        nullable=False,
    )
    status: Mapped[StatusContrato] = mapped_column(
        PgEnum(StatusContrato),
        default=StatusContrato.RASCUNHO,
        index=True,
    )
    
    # Valores
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    valor_entrada: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        comment="Valor de entrada (para tipo MISTO)",
    )
    percentual_exito: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="Percentual sobre êxito (ex: 30.00 = 30%)",
    )
    valor_hora: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Valor por hora (para tipo HORA)",
    )
    
    # Parcelamento
    numero_parcelas: Mapped[int] = mapped_column(default=1)
    dia_vencimento: Mapped[int | None] = mapped_column(
        comment="Dia do mês para vencimento das parcelas",
    )
    
    # Datas
    data_assinatura: Mapped[date | None] = mapped_column(Date)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date)
    
    # Documento do contrato (GCS)
    documento_path: Mapped[str | None] = mapped_column(
        String(500),
        comment="Path do contrato assinado no GCS",
    )
    
    # Observações
    descricao_servicos: Mapped[str | None] = mapped_column(
        Text,
        comment="Descrição dos serviços contratados",
    )
    observacoes: Mapped[str | None] = mapped_column(Text)
    
    # Relacionamentos
    cliente: Mapped["Cliente"] = relationship(  # noqa: F821
        "Cliente",
        foreign_keys=[cliente_id],
    )
    
    processo: Mapped["Processo"] = relationship(  # noqa: F821
        "Processo",
        foreign_keys=[processo_id],
    )
    
    advogado_responsavel: Mapped["Usuario"] = relationship(  # noqa: F821
        "Usuario",
        foreign_keys=[advogado_responsavel_id],
    )
    
    parcelas: Mapped[list["ParcelaHonorario"]] = relationship(
        "ParcelaHonorario",
        back_populates="contrato",
        lazy="selectin",
        order_by="ParcelaHonorario.numero_parcela",
    )
    
    @property
    def valor_pago(self) -> Decimal:
        """Calcula valor total pago."""
        return sum(
            p.valor_pago or Decimal("0")
            for p in self.parcelas
            if p.status == StatusParcela.PAGO
        )
    
    @property
    def valor_pendente(self) -> Decimal:
        """Calcula valor pendente."""
        return self.valor_total - self.valor_pago
    
    @property
    def percentual_pago(self) -> float:
        """Percentual já pago do contrato."""
        if self.valor_total == 0:
            return 0.0
        return float(self.valor_pago / self.valor_total * 100)
    
    def __repr__(self) -> str:
        return f"<ContratoHonorario(id={self.id}, tipo={self.tipo.value}, valor={self.valor_total})>"


class ParcelaHonorario(MultiTenantBase):
    """
    Parcela de pagamento de honorários.
    """
    
    __tablename__ = "parcelas_honorario"
    
    # Vinculação ao contrato
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contratos_honorario.id"),
        nullable=False,
        index=True,
    )
    
    # Identificação
    numero_parcela: Mapped[int] = mapped_column(nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255))
    
    # Valores
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    valor_pago: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    
    # Datas
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    data_pagamento: Mapped[date | None] = mapped_column(Date)
    
    # Status e forma de pagamento
    status: Mapped[StatusParcela] = mapped_column(
        PgEnum(StatusParcela),
        default=StatusParcela.PENDENTE,
        index=True,
    )
    forma_pagamento: Mapped[FormaPagamento | None] = mapped_column(
        PgEnum(FormaPagamento),
    )
    
    # Comprovante (GCS)
    comprovante_path: Mapped[str | None] = mapped_column(String(500))
    
    # Observações
    observacoes: Mapped[str | None] = mapped_column(Text)
    
    # Quem registrou o pagamento
    registrado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
    )
    
    # Relacionamentos
    contrato: Mapped["ContratoHonorario"] = relationship(
        "ContratoHonorario",
        back_populates="parcelas",
    )
    
    registrado_por: Mapped["Usuario"] = relationship(  # noqa: F821
        "Usuario",
        foreign_keys=[registrado_por_id],
    )
    
    @property
    def is_atrasada(self) -> bool:
        """Verifica se parcela está atrasada."""
        if self.status != StatusParcela.PENDENTE:
            return False
        return date.today() > self.data_vencimento
    
    @property
    def dias_atraso(self) -> int:
        """Calcula dias de atraso."""
        if not self.is_atrasada:
            return 0
        return (date.today() - self.data_vencimento).days
    
    def __repr__(self) -> str:
        return f"<ParcelaHonorario(id={self.id}, parcela={self.numero_parcela}, valor={self.valor})>"
