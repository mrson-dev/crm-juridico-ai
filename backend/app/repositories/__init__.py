"""Repositories - Data Access Layer."""

from app.repositories.base import BaseRepository, MultiTenantRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.escritorio_repository import EscritorioRepository
from app.repositories.honorario_repository import (
    ContratoHonorarioRepository,
    ParcelaHonorarioRepository,
)
from app.repositories.notificacao_repository import (
    NotificacaoRepository,
    PreferenciaNotificacaoRepository,
)
from app.repositories.processo_repository import (
    AndamentoRepository,
    PrazoRepository,
    ProcessoRepository,
)
from app.repositories.usuario_repository import UsuarioRepository

__all__ = [
    # Base
    "BaseRepository",
    "MultiTenantRepository",
    # Entidades
    "EscritorioRepository",
    "UsuarioRepository",
    "ClienteRepository",
    "ProcessoRepository",
    "PrazoRepository",
    "AndamentoRepository",
    "DocumentoRepository",
    "ContratoHonorarioRepository",
    "ParcelaHonorarioRepository",
    "NotificacaoRepository",
    "PreferenciaNotificacaoRepository",
]
