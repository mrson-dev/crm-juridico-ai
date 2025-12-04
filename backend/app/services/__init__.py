"""
Services Layer.

Camada de lógica de negócio do CRM Jurídico.
"""

from app.services.auth_service import AuthService
from app.services.cliente_service import ClienteService
from app.services.documento_service import DocumentoService
from app.services.escritorio_service import EscritorioService
from app.services.honorario_service import HonorarioService
from app.services.notificacao_service import NotificacaoService
from app.services.processo_service import ProcessoService

__all__ = [
    "AuthService",
    "ClienteService",
    "DocumentoService",
    "EscritorioService",
    "HonorarioService",
    "NotificacaoService",
    "ProcessoService",
]
