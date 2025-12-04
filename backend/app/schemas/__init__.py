"""Schemas Pydantic para validação de request/response."""

from app.schemas.base import (
    APIResponse,
    BaseSchema,
    ErrorDetail,
    ErrorResponse,
    IDMixin,
    PaginatedResponse,
    TimestampMixin,
)
from app.schemas.cliente import (
    ClienteCreate,
    ClienteFromDocumentAI,
    ClienteListResponse,
    ClienteResponse,
    ClienteUpdate,
)
from app.schemas.documento import (
    DocumentoCreate,
    DocumentoDownloadResponse,
    DocumentoExtracaoIA,
    DocumentoResponse,
    DocumentoUploadResponse,
)
from app.schemas.escritorio import (
    EscritorioCreate,
    EscritorioListResponse,
    EscritorioResponse,
    EscritorioUpdate,
)
from app.schemas.honorario import (
    ContratoCreate,
    ContratoListResponse,
    ContratoResponse,
    ContratoStats,
    ContratoUpdate,
    DashboardFinanceiro,
    ParcelaCreate,
    ParcelaListResponse,
    ParcelaRegistrarPagamento,
    ParcelaResponse,
    ParcelaUpdate,
)
from app.schemas.notificacao import (
    NotificacaoCreate,
    NotificacaoListResponse,
    NotificacaoMarcarLida,
    NotificacaoResponse,
    NotificacaoStats,
    PreferenciaNotificacaoResponse,
    PreferenciaNotificacaoUpdate,
)
from app.schemas.processo import (
    AndamentoCreate,
    AndamentoResponse,
    PrazoCreate,
    PrazoPendente,
    PrazoResponse,
    PrazoUpdate,
    ProcessoCreate,
    ProcessoListResponse,
    ProcessoResponse,
    ProcessoStats,
    ProcessoUpdate,
)
from app.schemas.usuario import (
    FirebaseLoginRequest,
    LoginRequest,
    LoginResponse,
    UsuarioCreate,
    UsuarioCreateFirebase,
    UsuarioListResponse,
    UsuarioMe,
    UsuarioResponse,
    UsuarioUpdate,
    UsuarioUpdatePassword,
)

__all__ = [
    # Base
    "BaseSchema",
    "APIResponse",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    "IDMixin",
    "TimestampMixin",
    # Escritório
    "EscritorioCreate",
    "EscritorioUpdate",
    "EscritorioResponse",
    "EscritorioListResponse",
    # Usuário
    "UsuarioCreate",
    "UsuarioCreateFirebase",
    "UsuarioUpdate",
    "UsuarioUpdatePassword",
    "UsuarioResponse",
    "UsuarioListResponse",
    "UsuarioMe",
    "LoginRequest",
    "LoginResponse",
    "FirebaseLoginRequest",
    # Cliente
    "ClienteCreate",
    "ClienteUpdate",
    "ClienteResponse",
    "ClienteListResponse",
    "ClienteFromDocumentAI",
    # Processo
    "ProcessoCreate",
    "ProcessoUpdate",
    "ProcessoResponse",
    "ProcessoListResponse",
    "ProcessoStats",
    "PrazoCreate",
    "PrazoUpdate",
    "PrazoResponse",
    "PrazoPendente",
    "AndamentoCreate",
    "AndamentoResponse",
    # Documento
    "DocumentoCreate",
    "DocumentoResponse",
    "DocumentoUploadResponse",
    "DocumentoDownloadResponse",
    "DocumentoExtracaoIA",
    # Honorários
    "ContratoCreate",
    "ContratoUpdate",
    "ContratoResponse",
    "ContratoListResponse",
    "ContratoStats",
    "ParcelaCreate",
    "ParcelaUpdate",
    "ParcelaResponse",
    "ParcelaListResponse",
    "ParcelaRegistrarPagamento",
    "DashboardFinanceiro",
    # Notificações
    "NotificacaoCreate",
    "NotificacaoResponse",
    "NotificacaoListResponse",
    "NotificacaoMarcarLida",
    "NotificacaoStats",
    "PreferenciaNotificacaoUpdate",
    "PreferenciaNotificacaoResponse",
]
