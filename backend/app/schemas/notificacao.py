"""
Schemas de Notificação.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.notificacao import (
    CanalNotificacao,
    StatusNotificacao,
    TipoNotificacao,
)
from app.schemas.base import BaseSchema, IDMixin, TimestampMixin


class NotificacaoBase(BaseSchema):
    """Campos base da notificação."""
    
    tipo: TipoNotificacao
    titulo: str = Field(..., max_length=255)
    mensagem: str
    canal: CanalNotificacao = CanalNotificacao.IN_APP


class NotificacaoCreate(NotificacaoBase):
    """Schema para criação de notificação."""
    
    usuario_id: UUID
    agendada_para: datetime | None = None
    action_url: str | None = None
    
    # Vinculações opcionais
    prazo_id: UUID | None = None
    processo_id: UUID | None = None
    andamento_id: UUID | None = None


class NotificacaoResponse(NotificacaoBase, IDMixin, TimestampMixin):
    """Schema de resposta da notificação."""
    
    escritorio_id: UUID
    usuario_id: UUID
    status: StatusNotificacao
    
    agendada_para: datetime | None
    enviada_em: datetime | None
    lida_em: datetime | None
    
    action_url: str | None
    prazo_id: UUID | None
    processo_id: UUID | None
    
    is_lida: bool


class NotificacaoListResponse(BaseSchema):
    """Schema para listagem de notificações."""
    
    id: UUID
    tipo: TipoNotificacao
    titulo: str
    mensagem: str
    status: StatusNotificacao
    created_at: datetime
    is_lida: bool
    action_url: str | None


class NotificacaoMarcarLida(BaseSchema):
    """Schema para marcar notificação como lida."""
    
    notificacao_ids: list[UUID] = Field(..., min_length=1)


class NotificacaoStats(BaseSchema):
    """Estatísticas de notificações."""
    
    total: int
    nao_lidas: int
    por_tipo: dict[str, int]


# === Preferências de Notificação ===

class PreferenciaNotificacaoBase(BaseSchema):
    """Campos base de preferências."""
    
    push_enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False
    
    prazo_vencendo_enabled: bool = True
    prazo_hoje_enabled: bool = True
    prazo_vencido_enabled: bool = True
    novo_andamento_enabled: bool = True
    mudanca_fase_enabled: bool = True


class PreferenciaNotificacaoUpdate(PreferenciaNotificacaoBase):
    """Schema para atualização de preferências."""
    
    fcm_token: str | None = None


class PreferenciaNotificacaoResponse(PreferenciaNotificacaoBase, IDMixin):
    """Schema de resposta das preferências."""
    
    usuario_id: UUID
    fcm_token: str | None = None
