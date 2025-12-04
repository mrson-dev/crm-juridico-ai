"""
Endpoints de Documentos.

Rotas para upload, download e processamento IA de documentos.
"""

import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.ai.gemini_service import gemini_service
from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession, EscritorioID
from app.core.exceptions import BusinessRuleError, ResourceNotFoundError, StorageError
from app.models.documento import CategoriaDocumento, TipoDocumento
from app.schemas.base import APIResponse, PaginatedResponse
from app.schemas.cliente import ClienteFromDocumentAI, ClienteResponse
from app.schemas.documento import (
    DocumentoCreate,
    DocumentoResponse,
    DocumentoStats,
    DocumentoUpdate,
)
from app.services.cliente_service import ClienteService
from app.services.documento_service import DocumentoService

router = APIRouter(prefix="/documentos", tags=["Documentos"])


# === UPLOAD E GESTÃO ===


@router.post("", response_model=APIResponse[DocumentoResponse])
async def upload_documento(
    db: DBSession,
    escritorio_id: EscritorioID,
    current_user: CurrentUser,
    file: UploadFile = File(..., description="Arquivo do documento"),
    tipo: TipoDocumento = Form(..., description="Tipo do documento"),
    cliente_id: UUID | None = Form(None, description="ID do cliente"),
    processo_id: UUID | None = Form(None, description="ID do processo"),
    descricao: str | None = Form(None, description="Descrição do documento"),
):
    """
    Faz upload de documento para o sistema.
    
    Armazena no Google Cloud Storage e registra metadados.
    """
    # Valida tipo de arquivo
    if file.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não suportado: {file.content_type}",
        )
    
    # Lê conteúdo
    content = await file.read()
    
    # Valida tamanho
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Arquivo muito grande. Máximo: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )
    
    try:
        service = DocumentoService(db, escritorio_id)
        
        dados = DocumentoCreate(
            tipo=tipo,
            cliente_id=cliente_id,
            processo_id=processo_id,
            descricao=descricao,
        )
        
        documento = await service.upload_documento(
            dados=dados,
            file_content=content,
            filename=file.filename or "documento",
            content_type=file.content_type,
            uploaded_by_id=current_user.id,
        )
        
        return APIResponse(
            success=True,
            data=DocumentoResponse.model_validate(documento),
            message="Documento enviado com sucesso",
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao armazenar arquivo: {e}",
        )


@router.get("", response_model=PaginatedResponse[DocumentoResponse])
async def listar_documentos(
    db: DBSession,
    escritorio_id: EscritorioID,
    cliente_id: UUID | None = None,
    processo_id: UUID | None = None,
    tipo: TipoDocumento | None = None,
    categoria: CategoriaDocumento | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Lista documentos com filtros."""
    service = DocumentoService(db, escritorio_id)
    
    if cliente_id:
        documentos = await service.listar_documentos_cliente(cliente_id, categoria)
    elif processo_id:
        documentos = await service.listar_documentos_processo(processo_id, tipo)
    else:
        documentos = []  # Requer filtro
    
    return PaginatedResponse(
        success=True,
        data=[DocumentoResponse.model_validate(d) for d in documentos],
        total=len(documentos),
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get("/pendentes", response_model=APIResponse[list[DocumentoResponse]])
async def listar_pendentes_processamento(
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Lista documentos aguardando processamento IA."""
    service = DocumentoService(db, escritorio_id)
    documentos = await service.listar_pendentes_processamento()
    
    return APIResponse(
        success=True,
        data=[DocumentoResponse.model_validate(d) for d in documentos],
    )


@router.get("/stats", response_model=APIResponse[DocumentoStats])
async def get_stats(
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Retorna estatísticas dos documentos."""
    service = DocumentoService(db, escritorio_id)
    stats = await service.get_stats()
    
    return APIResponse(success=True, data=stats)


@router.get("/{documento_id}", response_model=APIResponse[DocumentoResponse])
async def buscar_documento(
    documento_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Busca documento por ID."""
    try:
        service = DocumentoService(db, escritorio_id)
        documento = await service.buscar_documento(documento_id)
        
        return APIResponse(
            success=True,
            data=DocumentoResponse.model_validate(documento),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{documento_id}/download-url", response_model=APIResponse[str])
async def gerar_url_download(
    documento_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
    expiration_minutes: int = Query(30, ge=5, le=1440),
):
    """
    Gera URL assinada temporária para download.
    
    A URL expira após o tempo especificado (padrão: 30 minutos).
    """
    try:
        service = DocumentoService(db, escritorio_id)
        url = await service.gerar_url_download(documento_id, expiration_minutes)
        
        return APIResponse(success=True, data=url)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{documento_id}", response_model=APIResponse[DocumentoResponse])
async def atualizar_documento(
    documento_id: UUID,
    dados: DocumentoUpdate,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Atualiza metadados do documento."""
    try:
        service = DocumentoService(db, escritorio_id)
        documento = await service.atualizar_documento(documento_id, dados)
        
        return APIResponse(
            success=True,
            data=DocumentoResponse.model_validate(documento),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{documento_id}", response_model=APIResponse)
async def excluir_documento(
    documento_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Remove documento (soft delete)."""
    try:
        service = DocumentoService(db, escritorio_id)
        await service.excluir_documento(documento_id)
        
        return APIResponse(
            success=True,
            message="Documento removido",
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# === PROCESSAMENTO IA ===


@router.post("/{documento_id}/processar-ia", response_model=APIResponse[DocumentoResponse])
async def processar_documento_ia(
    documento_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """
    Processa documento com IA (Gemini/Document AI).
    
    Extrai dados estruturados de acordo com o tipo do documento.
    """
    try:
        service = DocumentoService(db, escritorio_id)
        documento = await service.processar_com_ia(documento_id)
        
        return APIResponse(
            success=True,
            data=DocumentoResponse.model_validate(documento),
            message="Documento processado com IA",
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# === EXTRAÇÃO DIRETA (sem salvar documento) ===


@router.post(
    "/extract-identity",
    response_model=APIResponse[ClienteFromDocumentAI],
)
async def extrair_documento_identidade(
    current_user: CurrentUser,
    file: UploadFile = File(..., description="Documento de identificação (RG, CNH, CPF)"),
) -> APIResponse[ClienteFromDocumentAI]:
    """
    Extrai dados de documento de identificação usando IA.
    
    Aceita imagens (JPG, PNG, WebP) ou PDF.
    Retorna dados estruturados para preenchimento de cadastro.
    """
    if file.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não suportado: {file.content_type}",
        )
    
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Arquivo muito grande. Máximo: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )
    
    suffix = Path(file.filename or "document").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        dados = await gemini_service.extract_identity_document(tmp_path)
        
        return APIResponse(
            success=True,
            data=dados,
            message=f"Extração concluída com {dados.confidence:.0%} de confiança",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post(
    "/extract-identity/{cliente_id}",
    response_model=APIResponse[ClienteResponse],
)
async def extrair_e_preencher_cliente(
    cliente_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    file: UploadFile = File(..., description="Documento de identificação"),
) -> APIResponse[ClienteResponse]:
    """
    Extrai dados de documento e preenche cadastro do cliente.
    
    Apenas preenche campos vazios, não sobrescreve dados existentes.
    """
    if file.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não suportado: {file.content_type}",
        )
    
    content = await file.read()
    suffix = Path(file.filename or "document").suffix or ".pdf"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        dados_ia = await gemini_service.extract_identity_document(tmp_path)
        
        service = ClienteService(db, current_user.escritorio_id)
        cliente = await service.preencher_com_dados_ia(cliente_id, dados_ia)
        
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado",
            )
        
        return APIResponse(
            success=True,
            data=ClienteResponse.model_validate(cliente),
            message=f"Dados extraídos e aplicados com {dados_ia.confidence:.0%} de confiança",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/extract-cnis", response_model=APIResponse[dict])
async def extrair_cnis(
    current_user: CurrentUser,
    file: UploadFile = File(..., description="Arquivo CNIS (PDF ou imagem)"),
) -> APIResponse[dict]:
    """
    Extrai dados do CNIS usando IA.
    
    Retorna vínculos empregatícios e contribuições.
    """
    if file.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não suportado: {file.content_type}",
        )
    
    content = await file.read()
    suffix = Path(file.filename or "cnis").suffix or ".pdf"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        dados = await gemini_service.extract_cnis(tmp_path)
        return APIResponse(success=True, data=dados)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/analyze-ppp", response_model=APIResponse[dict])
async def analisar_ppp(
    current_user: CurrentUser,
    file: UploadFile = File(..., description="Arquivo PPP (PDF ou imagem)"),
) -> APIResponse[dict]:
    """
    Analisa PPP para identificar tempo especial.
    
    Identifica exposição a agentes nocivos para aposentadoria especial.
    """
    if file.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não suportado: {file.content_type}",
        )
    
    content = await file.read()
    suffix = Path(file.filename or "ppp").suffix or ".pdf"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        dados = await gemini_service.analyze_ppp(tmp_path)
        return APIResponse(success=True, data=dados)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/summarize", response_model=APIResponse[str])
async def resumir_documento(
    current_user: CurrentUser,
    file: UploadFile = File(..., description="Documento jurídico"),
) -> APIResponse[str]:
    """
    Gera resumo de documento jurídico usando IA.
    
    Identifica tipo, partes, objeto, decisão e prazos.
    """
    if file.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não suportado: {file.content_type}",
        )
    
    content = await file.read()
    suffix = Path(file.filename or "document").suffix or ".pdf"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        resumo = await gemini_service.summarize_document(tmp_path)
        return APIResponse(success=True, data=resumo)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
