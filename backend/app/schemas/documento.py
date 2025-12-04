"""
Schemas de Documento.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.documento import StatusProcessamentoIA, TipoDocumento
from app.schemas.base import BaseSchema, IDMixin, TimestampMixin


class DocumentoBase(BaseSchema):
    """Campos base do documento."""
    
    nome: str = Field(..., min_length=1, max_length=255)
    tipo: TipoDocumento = TipoDocumento.OUTROS
    descricao: str | None = None


class DocumentoCreate(DocumentoBase):
    """Schema para criação de documento (upload)."""
    
    cliente_id: UUID | None = None
    processo_id: UUID | None = None


class DocumentoUpdate(BaseSchema):
    """Schema para atualização de documento."""
    
    nome: str | None = None
    tipo: TipoDocumento | None = None
    descricao: str | None = None
    cliente_id: UUID | None = None
    processo_id: UUID | None = None


class DocumentoResponse(DocumentoBase, IDMixin, TimestampMixin):
    """Schema de resposta do documento."""
    
    escritorio_id: UUID
    cliente_id: UUID | None
    processo_id: UUID | None
    uploaded_by_id: UUID
    
    gcs_bucket: str
    gcs_path: str
    mime_type: str
    tamanho_bytes: int
    
    versao: int
    documento_original_id: UUID | None
    
    status_ia: StatusProcessamentoIA
    resumo_ia: str | None
    processado_em: datetime | None
    
    is_processado: bool


class DocumentoUploadResponse(BaseSchema):
    """Resposta após upload de documento."""
    
    documento: DocumentoResponse
    url_upload: str | None = None  # URL assinada para upload direto ao GCS


class DocumentoDownloadResponse(BaseSchema):
    """Resposta com URL para download."""
    
    documento_id: UUID
    nome: str
    url_download: str
    expires_in_seconds: int = 3600


class DocumentoExtracaoIA(BaseSchema):
    """Resultado da extração de IA de um documento."""
    
    documento_id: UUID
    tipo_documento: TipoDocumento
    dados_extraidos: dict
    resumo: str | None
    confidence: float = Field(ge=0, le=1)
    campos_extraidos: list[str]
    campos_para_revisao: list[str]


class DocumentoStats(BaseSchema):
    """Estatísticas de documentos."""
    
    total: int
    por_tipo: dict[str, int]
    por_status_ia: dict[str, int]
    tamanho_total_bytes: int
    pendentes_processamento: int
