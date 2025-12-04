"""
Modelos relacionados a Processos Judiciais.

Inclui Processo, Prazo e Andamento.
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import MultiTenantBase, PgEnum


class TipoBeneficio(str, enum.Enum):
    """Tipos de benefícios previdenciários."""
    
    # Aposentadorias
    APOSENTADORIA_IDADE = "aposentadoria_idade"
    APOSENTADORIA_TEMPO_CONTRIBUICAO = "aposentadoria_tempo_contribuicao"
    APOSENTADORIA_ESPECIAL = "aposentadoria_especial"
    APOSENTADORIA_RURAL = "aposentadoria_rural"
    APOSENTADORIA_INVALIDEZ = "aposentadoria_invalidez"
    APOSENTADORIA_PROGRAMADA = "aposentadoria_programada"  # Pós-reforma
    
    # Benefícios por incapacidade
    AUXILIO_DOENCA = "auxilio_doenca"
    AUXILIO_ACIDENTE = "auxilio_acidente"
    BPC_LOAS_IDOSO = "bpc_loas_idoso"
    BPC_LOAS_DEFICIENCIA = "bpc_loas_deficiencia"
    
    # Pensões
    PENSAO_MORTE = "pensao_morte"
    AUXILIO_RECLUSAO = "auxilio_reclusao"
    
    # Outros
    SALARIO_MATERNIDADE = "salario_maternidade"
    REVISAO_BENEFICIO = "revisao_beneficio"
    OUTROS = "outros"


class FaseProcessual(str, enum.Enum):
    """Fases do processo judicial/administrativo."""
    
    # Administrativo
    REQUERIMENTO_ADMINISTRATIVO = "requerimento_administrativo"
    RECURSO_ADMINISTRATIVO = "recurso_administrativo"
    
    # Judicial - Primeira Instância
    INICIAL_PROTOCOLADA = "inicial_protocolada"
    CITACAO = "citacao"
    CONTESTACAO = "contestacao"
    PERICIA_AGENDADA = "pericia_agendada"
    PERICIA_REALIZADA = "pericia_realizada"
    ALEGACOES_FINAIS = "alegacoes_finais"
    SENTENCA = "sentenca"
    
    # Recursos
    RECURSO_INSS = "recurso_inss"
    CONTRARRAZOES = "contrarrazoes"
    TRIBUNAL = "tribunal"
    ACORDAO = "acordao"
    
    # Execução
    EXECUCAO = "execucao"
    RPV_PRECATORIO = "rpv_precatorio"
    
    # Encerramento
    ARQUIVADO = "arquivado"
    TRANSITADO_JULGADO = "transitado_julgado"


class StatusPrazo(str, enum.Enum):
    """Status do prazo processual."""
    
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CUMPRIDO = "cumprido"
    PERDIDO = "perdido"
    CANCELADO = "cancelado"


class TipoPrazo(str, enum.Enum):
    """Tipos de prazos processuais."""
    
    CONTESTACAO = "contestacao"
    RECURSO = "recurso"
    MANIFESTACAO = "manifestacao"
    PERICIA = "pericia"
    AUDIENCIA = "audiencia"
    CUMPRIMENTO_SENTENCA = "cumprimento_sentenca"
    JUNTADA_DOCUMENTOS = "juntada_documentos"
    OUTROS = "outros"


class Processo(MultiTenantBase):
    """
    Processo judicial ou administrativo.
    
    Pode ser um requerimento administrativo no INSS ou
    processo judicial em qualquer instância.
    """
    
    __tablename__ = "processos"
    
    # Identificação do processo
    numero_cnj: Mapped[str | None] = mapped_column(
        String(25),
        unique=True,
        index=True,
        comment="Formato: NNNNNNN-DD.AAAA.J.TR.OOOO",
    )
    numero_administrativo: Mapped[str | None] = mapped_column(
        String(30),
        index=True,
        comment="Número do requerimento no INSS",
    )
    
    # Tipo de benefício/ação
    tipo_beneficio: Mapped[TipoBeneficio] = mapped_column(
        PgEnum(TipoBeneficio),
        nullable=False,
    )
    
    # Fase atual
    fase: Mapped[FaseProcessual] = mapped_column(
        PgEnum(FaseProcessual),
        default=FaseProcessual.REQUERIMENTO_ADMINISTRATIVO,
    )
    
    # Localização (judicial)
    tribunal: Mapped[str | None] = mapped_column(String(20))  # TRF1, TRF3, etc.
    vara: Mapped[str | None] = mapped_column(String(100))
    comarca: Mapped[str | None] = mapped_column(String(100))
    
    # Localização (administrativo)
    agencia_inss: Mapped[str | None] = mapped_column(String(100))
    
    # Datas importantes
    data_entrada: Mapped[date] = mapped_column(Date, nullable=False)
    data_distribuicao: Mapped[date | None] = mapped_column(Date)
    data_citacao: Mapped[date | None] = mapped_column(Date)
    data_sentenca: Mapped[date | None] = mapped_column(Date)
    data_transito: Mapped[date | None] = mapped_column(Date)
    
    # Valores
    valor_causa: Mapped[float | None] = mapped_column()
    valor_condenacao: Mapped[float | None] = mapped_column()
    
    # Descrição e observações
    objeto: Mapped[str | None] = mapped_column(Text, comment="Descrição do pedido")
    observacoes: Mapped[str | None] = mapped_column(Text)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Resultado (quando encerrado)
    resultado: Mapped[str | None] = mapped_column(
        String(50),
        comment="procedente, improcedente, acordo, desistencia",
    )
    
    # Cliente (autor/requerente)
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clientes.id"),
        nullable=False,
        index=True,
    )
    
    # Advogado responsável
    advogado_responsavel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
    )
    
    # Relacionamentos
    cliente: Mapped["Cliente"] = relationship(  # noqa: F821
        "Cliente",
        back_populates="processos",
    )
    
    advogado_responsavel: Mapped["Usuario"] = relationship(  # noqa: F821
        "Usuario",
        foreign_keys=[advogado_responsavel_id],
    )
    
    prazos: Mapped[list["Prazo"]] = relationship(
        "Prazo",
        back_populates="processo",
        lazy="selectin",
        order_by="Prazo.data_fatal",
    )
    
    andamentos: Mapped[list["Andamento"]] = relationship(
        "Andamento",
        back_populates="processo",
        lazy="selectin",
        order_by="desc(Andamento.data)",
    )
    
    documentos: Mapped[list["Documento"]] = relationship(  # noqa: F821
        "Documento",
        back_populates="processo",
        lazy="selectin",
    )
    
    @property
    def numero_principal(self) -> str:
        """Retorna o número principal do processo (CNJ ou administrativo)."""
        return self.numero_cnj or self.numero_administrativo or "Sem número"
    
    @property
    def proximo_prazo(self) -> "Prazo | None":
        """Retorna o próximo prazo pendente."""
        for prazo in self.prazos:
            if prazo.status == StatusPrazo.PENDENTE:
                return prazo
        return None
    
    def __repr__(self) -> str:
        return f"<Processo(id={self.id}, numero='{self.numero_principal}')>"


class Prazo(MultiTenantBase):
    """
    Prazo processual.
    
    ⚠️ CRÍTICO: Prazos são a funcionalidade mais importante do sistema.
    Perder um prazo pode causar danos irreparáveis ao cliente.
    """
    
    __tablename__ = "prazos"
    
    # Vinculação ao processo
    processo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processos.id"),
        nullable=False,
        index=True,
    )
    
    # Dados do prazo
    tipo: Mapped[TipoPrazo] = mapped_column(PgEnum(TipoPrazo), nullable=False)
    descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Datas
    data_fatal: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Data limite para cumprimento",
    )
    data_inicio: Mapped[date | None] = mapped_column(
        Date,
        comment="Data de início da contagem",
    )
    dias_prazo: Mapped[int | None] = mapped_column(Integer)
    
    # Status
    status: Mapped[StatusPrazo] = mapped_column(
        PgEnum(StatusPrazo),
        default=StatusPrazo.PENDENTE,
        nullable=False,
        index=True,
    )
    
    # Controle de cumprimento
    data_cumprimento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cumprido_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
    )
    
    # Notificações
    notificacao_enviada: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Observações
    observacoes: Mapped[str | None] = mapped_column(Text)
    
    # Relacionamentos
    processo: Mapped["Processo"] = relationship(
        "Processo",
        back_populates="prazos",
    )
    
    cumprido_por: Mapped["Usuario"] = relationship(  # noqa: F821
        "Usuario",
        foreign_keys=[cumprido_por_id],
    )
    
    @property
    def dias_restantes(self) -> int:
        """Calcula dias restantes até o prazo fatal."""
        if self.status != StatusPrazo.PENDENTE:
            return 0
        return (self.data_fatal - date.today()).days
    
    @property
    def is_urgente(self) -> bool:
        """Prazo é urgente se faltam 3 dias ou menos."""
        return 0 < self.dias_restantes <= 3
    
    @property
    def is_vencido(self) -> bool:
        """Verifica se prazo está vencido."""
        return self.dias_restantes < 0 and self.status == StatusPrazo.PENDENTE
    
    def __repr__(self) -> str:
        return f"<Prazo(id={self.id}, tipo={self.tipo.value}, data_fatal={self.data_fatal})>"


class Andamento(MultiTenantBase):
    """
    Movimentação/andamento processual.
    
    Registra cada evento relevante do processo.
    """
    
    __tablename__ = "andamentos"
    
    # Vinculação ao processo
    processo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processos.id"),
        nullable=False,
        index=True,
    )
    
    # Dados do andamento
    data: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Origem do andamento
    fonte: Mapped[str | None] = mapped_column(
        String(50),
        comment="manual, pje, esaj, push",
    )
    
    # Flags
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    gera_prazo: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Quem registrou (se manual)
    registrado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
    )
    
    # Relacionamentos
    processo: Mapped["Processo"] = relationship(
        "Processo",
        back_populates="andamentos",
    )
    
    registrado_por: Mapped["Usuario"] = relationship(  # noqa: F821
        "Usuario",
        foreign_keys=[registrado_por_id],
    )
    
    def __repr__(self) -> str:
        return f"<Andamento(id={self.id}, data={self.data}, processo_id={self.processo_id})>"
