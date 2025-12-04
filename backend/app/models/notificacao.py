"""
Modelo de Notificação.

Gerencia notificações de prazos, andamentos e alertas do sistema.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import MultiTenantBase, PgEnum


class TipoNotificacao(str, enum.Enum):
    """Tipos de notificação."""
    
    # Prazos
    PRAZO_VENCENDO = "prazo_vencendo"  # X dias antes
    PRAZO_HOJE = "prazo_hoje"  # No dia
    PRAZO_VENCIDO = "prazo_vencido"  # Após vencer
    
    # Processos
    NOVO_ANDAMENTO = "novo_andamento"
    MUDANCA_FASE = "mudanca_fase"
    DOCUMENTO_PROCESSADO = "documento_processado"
    
    # Sistema
    SISTEMA = "sistema"
    ALERTA = "alerta"


class CanalNotificacao(str, enum.Enum):
    """Canais de envio da notificação."""
    
    PUSH = "push"  # Firebase Cloud Messaging
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"  # Apenas no sistema


class StatusNotificacao(str, enum.Enum):
    """Status da notificação."""
    
    PENDENTE = "pendente"
    ENVIADA = "enviada"
    LIDA = "lida"
    FALHA = "falha"


class Notificacao(MultiTenantBase):
    """
    Notificação do sistema.
    
    Gerencia alertas de prazos, andamentos e comunicações.
    """
    
    __tablename__ = "notificacoes"
    
    # Tipo e conteúdo
    tipo: Mapped[TipoNotificacao] = mapped_column(
        PgEnum(TipoNotificacao),
        nullable=False,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Canal e status
    canal: Mapped[CanalNotificacao] = mapped_column(
        PgEnum(CanalNotificacao),
        default=CanalNotificacao.IN_APP,
    )
    status: Mapped[StatusNotificacao] = mapped_column(
        PgEnum(StatusNotificacao),
        default=StatusNotificacao.PENDENTE,
        index=True,
    )
    
    # Datas
    agendada_para: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
        comment="Data/hora agendada para envio",
    )
    enviada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Tentativas de envio
    tentativas: Mapped[int] = mapped_column(default=0)
    erro_envio: Mapped[str | None] = mapped_column(Text)
    
    # Links e ações
    action_url: Mapped[str | None] = mapped_column(
        String(500),
        comment="URL para ação ao clicar na notificação",
    )
    
    # Vinculações
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
        comment="Destinatário da notificação",
    )
    
    prazo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prazos.id"),
        index=True,
    )
    
    processo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processos.id"),
        index=True,
    )
    
    andamento_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("andamentos.id"),
    )
    
    # Relacionamentos
    usuario: Mapped["Usuario"] = relationship(  # noqa: F821
        "Usuario",
        foreign_keys=[usuario_id],
    )
    
    prazo: Mapped["Prazo"] = relationship(  # noqa: F821
        "Prazo",
        foreign_keys=[prazo_id],
    )
    
    processo: Mapped["Processo"] = relationship(  # noqa: F821
        "Processo",
        foreign_keys=[processo_id],
    )
    
    @property
    def is_lida(self) -> bool:
        """Verifica se notificação foi lida."""
        return self.status == StatusNotificacao.LIDA
    
    @property
    def is_pendente(self) -> bool:
        """Verifica se notificação está pendente de envio."""
        return self.status == StatusNotificacao.PENDENTE
    
    def __repr__(self) -> str:
        return f"<Notificacao(id={self.id}, tipo={self.tipo.value}, status={self.status.value})>"


class PreferenciaNotificacao(MultiTenantBase):
    """
    Preferências de notificação por usuário.
    
    Define quais tipos de notificação o usuário quer receber e por qual canal.
    """
    
    __tablename__ = "preferencias_notificacao"
    
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    
    # Canais habilitados
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Tipos habilitados
    prazo_vencendo_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    prazo_hoje_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    prazo_vencido_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    novo_andamento_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    mudanca_fase_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # FCM token para push notifications
    fcm_token: Mapped[str | None] = mapped_column(
        String(500),
        comment="Firebase Cloud Messaging token",
    )
    
    # Relacionamento
    usuario: Mapped["Usuario"] = relationship(  # noqa: F821
        "Usuario",
        foreign_keys=[usuario_id],
    )
    
    def __repr__(self) -> str:
        return f"<PreferenciaNotificacao(usuario_id={self.usuario_id})>"
