"""
Endpoints de Processos.

Rotas para gerenciamento de processos, prazos e andamentos.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DBSession, EscritorioID
from app.core.exceptions import (
    BusinessRuleError,
    ProcessoArquivadoError,
    ResourceNotFoundError,
)
from app.models.processo import FaseProcessual
from app.schemas.base import APIResponse, PaginatedResponse
from app.schemas.processo import (
    AndamentoCreate,
    AndamentoResponse,
    PrazoCreate,
    PrazoResponse,
    PrazoUpdate,
    ProcessoCreate,
    ProcessoResponse,
    ProcessoStats,
    ProcessoUpdate,
)
from app.services.processo_service import ProcessoService

router = APIRouter(prefix="/processos", tags=["Processos"])


# === PROCESSOS ===


@router.post("", response_model=APIResponse[ProcessoResponse])
async def criar_processo(
    dados: ProcessoCreate,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Cria novo processo."""
    try:
        service = ProcessoService(db, escritorio_id)
        processo = await service.criar_processo(dados)
        
        return APIResponse(
            success=True,
            data=ProcessoResponse.model_validate(processo),
            message="Processo criado com sucesso",
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=PaginatedResponse[ProcessoResponse])
async def listar_processos(
    db: DBSession,
    escritorio_id: EscritorioID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    fase: FaseProcessual | None = None,
    cliente_id: UUID | None = None,
    include_archived: bool = False,
):
    """Lista processos com filtros."""
    service = ProcessoService(db, escritorio_id)
    processos = await service.listar_processos(
        skip=skip,
        limit=limit,
        fase=fase,
        cliente_id=cliente_id,
        include_archived=include_archived,
    )
    
    return PaginatedResponse(
        success=True,
        data=[ProcessoResponse.model_validate(p) for p in processos],
        total=len(processos),
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get("/search", response_model=APIResponse[list[ProcessoResponse]])
async def pesquisar_processos(
    db: DBSession,
    escritorio_id: EscritorioID,
    q: str = Query(..., min_length=3, description="Termo de busca"),
):
    """Pesquisa processos por número ou objeto."""
    service = ProcessoService(db, escritorio_id)
    processos = await service.pesquisar_processos(q)
    
    return APIResponse(
        success=True,
        data=[ProcessoResponse.model_validate(p) for p in processos],
    )


@router.get("/stats", response_model=APIResponse[ProcessoStats])
async def get_stats(
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Retorna estatísticas dos processos."""
    service = ProcessoService(db, escritorio_id)
    stats = await service.get_stats()
    
    return APIResponse(success=True, data=stats)


@router.get("/{processo_id}", response_model=APIResponse[ProcessoResponse])
async def buscar_processo(
    processo_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
    with_relations: bool = False,
):
    """Busca processo por ID."""
    try:
        service = ProcessoService(db, escritorio_id)
        processo = await service.buscar_processo(processo_id, with_relations)
        
        return APIResponse(
            success=True,
            data=ProcessoResponse.model_validate(processo),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{processo_id}", response_model=APIResponse[ProcessoResponse])
async def atualizar_processo(
    processo_id: UUID,
    dados: ProcessoUpdate,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Atualiza processo."""
    try:
        service = ProcessoService(db, escritorio_id)
        processo = await service.atualizar_processo(processo_id, dados)
        
        return APIResponse(
            success=True,
            data=ProcessoResponse.model_validate(processo),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ProcessoArquivadoError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{processo_id}/arquivar", response_model=APIResponse[ProcessoResponse])
async def arquivar_processo(
    processo_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Arquiva processo encerrado."""
    try:
        service = ProcessoService(db, escritorio_id)
        processo = await service.arquivar_processo(processo_id)
        
        return APIResponse(
            success=True,
            data=ProcessoResponse.model_validate(processo),
            message="Processo arquivado",
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# === PRAZOS ===


@router.post("/prazos", response_model=APIResponse[PrazoResponse])
async def criar_prazo(
    dados: PrazoCreate,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """
    Cria novo prazo processual.
    
    ⚠️ Prazos são críticos - perda pode causar danos ao cliente.
    """
    try:
        service = ProcessoService(db, escritorio_id)
        prazo = await service.criar_prazo(dados)
        
        return APIResponse(
            success=True,
            data=PrazoResponse.model_validate(prazo),
            message="Prazo criado com sucesso",
        )
    except (ResourceNotFoundError, ProcessoArquivadoError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/prazos/pendentes", response_model=APIResponse[list[PrazoResponse]])
async def listar_prazos_pendentes(
    db: DBSession,
    escritorio_id: EscritorioID,
    dias_futuros: int = Query(30, ge=1, le=365),
):
    """Lista prazos pendentes."""
    service = ProcessoService(db, escritorio_id)
    prazos = await service.listar_prazos_pendentes(dias_futuros)
    
    return APIResponse(
        success=True,
        data=[PrazoResponse.model_validate(p) for p in prazos],
    )


@router.get("/prazos/urgentes", response_model=APIResponse[list[PrazoResponse]])
async def listar_prazos_urgentes(
    db: DBSession,
    escritorio_id: EscritorioID,
    dias: int = Query(3, ge=1, le=30),
):
    """Lista prazos urgentes (próximos X dias)."""
    service = ProcessoService(db, escritorio_id)
    prazos = await service.listar_prazos_urgentes(dias)
    
    return APIResponse(
        success=True,
        data=[PrazoResponse.model_validate(p) for p in prazos],
    )


@router.get("/prazos/vencidos", response_model=APIResponse[list[PrazoResponse]])
async def listar_prazos_vencidos(
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Lista prazos vencidos não cumpridos."""
    service = ProcessoService(db, escritorio_id)
    prazos = await service.listar_prazos_vencidos()
    
    return APIResponse(
        success=True,
        data=[PrazoResponse.model_validate(p) for p in prazos],
    )


@router.put("/prazos/{prazo_id}", response_model=APIResponse[PrazoResponse])
async def atualizar_prazo(
    prazo_id: UUID,
    dados: PrazoUpdate,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Atualiza prazo."""
    try:
        service = ProcessoService(db, escritorio_id)
        prazo = await service.atualizar_prazo(prazo_id, dados)
        
        return APIResponse(
            success=True,
            data=PrazoResponse.model_validate(prazo),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/prazos/{prazo_id}/cumprir", response_model=APIResponse[PrazoResponse])
async def cumprir_prazo(
    prazo_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
    current_user: CurrentUser,
):
    """Marca prazo como cumprido."""
    try:
        service = ProcessoService(db, escritorio_id)
        prazo = await service.cumprir_prazo(prazo_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=PrazoResponse.model_validate(prazo),
            message="Prazo marcado como cumprido",
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# === ANDAMENTOS ===


@router.post("/andamentos", response_model=APIResponse[AndamentoResponse])
async def criar_andamento(
    dados: AndamentoCreate,
    db: DBSession,
    escritorio_id: EscritorioID,
    current_user: CurrentUser,
):
    """Registra novo andamento processual."""
    try:
        service = ProcessoService(db, escritorio_id)
        andamento = await service.criar_andamento(dados, current_user.id)
        
        return APIResponse(
            success=True,
            data=AndamentoResponse.model_validate(andamento),
            message="Andamento registrado",
        )
    except (ResourceNotFoundError, ProcessoArquivadoError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{processo_id}/andamentos",
    response_model=PaginatedResponse[AndamentoResponse],
)
async def listar_andamentos(
    processo_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Lista andamentos de um processo."""
    service = ProcessoService(db, escritorio_id)
    andamentos = await service.listar_andamentos(processo_id, skip, limit)
    
    return PaginatedResponse(
        success=True,
        data=[AndamentoResponse.model_validate(a) for a in andamentos],
        total=len(andamentos),
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get("/andamentos/recentes", response_model=APIResponse[list[AndamentoResponse]])
async def listar_andamentos_recentes(
    db: DBSession,
    escritorio_id: EscritorioID,
    dias: int = Query(7, ge=1, le=30),
):
    """Lista andamentos recentes do escritório."""
    service = ProcessoService(db, escritorio_id)
    andamentos = await service.listar_andamentos_recentes(dias)
    
    return APIResponse(
        success=True,
        data=[AndamentoResponse.model_validate(a) for a in andamentos],
    )
