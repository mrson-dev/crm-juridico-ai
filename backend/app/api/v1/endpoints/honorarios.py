"""
Endpoints de Honorários.

Rotas para gerenciamento de contratos, parcelas e pagamentos.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DBSession, EscritorioID
from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.schemas.base import APIResponse, PaginatedResponse
from app.schemas.honorario import (
    ContratoCreate,
    ContratoResponse,
    ContratoUpdate,
    DashboardFinanceiro,
    ParcelaCreate,
    ParcelaRegistrarPagamento,
    ParcelaResponse,
    ParcelaUpdate,
    ResumoFinanceiro,
)
from app.services.honorario_service import HonorarioService

router = APIRouter(prefix="/honorarios", tags=["Honorários"])


# === CONTRATOS ===


@router.post("/contratos", response_model=APIResponse[ContratoResponse])
async def criar_contrato(
    dados: ContratoCreate,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """
    Cria novo contrato de honorários.
    
    Se tipo for PARCELADO, parcelas podem ser geradas automaticamente.
    """
    try:
        service = HonorarioService(db, escritorio_id)
        contrato = await service.criar_contrato(dados)
        
        return APIResponse(
            success=True,
            data=ContratoResponse.model_validate(contrato),
            message="Contrato criado com sucesso",
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/contratos",
    response_model=PaginatedResponse[ContratoResponse],
)
async def listar_contratos(
    db: DBSession,
    escritorio_id: EscritorioID,
    cliente_id: UUID | None = None,
    processo_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Lista contratos de honorários."""
    service = HonorarioService(db, escritorio_id)
    
    if cliente_id:
        contratos = await service.listar_contratos_cliente(cliente_id)
    elif processo_id:
        contratos = await service.listar_contratos_processo(processo_id)
    else:
        # Lista geral (implementar no repository se necessário)
        contratos = await service.listar_contratos_cliente(cliente_id) if cliente_id else []
    
    return PaginatedResponse(
        success=True,
        data=[ContratoResponse.model_validate(c) for c in contratos],
        total=len(contratos),
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get(
    "/contratos/{contrato_id}",
    response_model=APIResponse[ContratoResponse],
)
async def buscar_contrato(
    contrato_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
    with_parcelas: bool = False,
):
    """Busca contrato por ID."""
    try:
        service = HonorarioService(db, escritorio_id)
        contrato = await service.buscar_contrato(contrato_id, with_parcelas)
        
        return APIResponse(
            success=True,
            data=ContratoResponse.model_validate(contrato),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put(
    "/contratos/{contrato_id}",
    response_model=APIResponse[ContratoResponse],
)
async def atualizar_contrato(
    contrato_id: UUID,
    dados: ContratoUpdate,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Atualiza contrato de honorários."""
    try:
        service = HonorarioService(db, escritorio_id)
        contrato = await service.atualizar_contrato(contrato_id, dados)
        
        return APIResponse(
            success=True,
            data=ContratoResponse.model_validate(contrato),
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


@router.post(
    "/contratos/{contrato_id}/ativar",
    response_model=APIResponse[ContratoResponse],
)
async def ativar_contrato(
    contrato_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Ativa contrato (sai de rascunho)."""
    try:
        service = HonorarioService(db, escritorio_id)
        contrato = await service.ativar_contrato(contrato_id)
        
        return APIResponse(
            success=True,
            data=ContratoResponse.model_validate(contrato),
            message="Contrato ativado",
        )
    except (ResourceNotFoundError, BusinessRuleError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/contratos/{contrato_id}/cancelar",
    response_model=APIResponse[ContratoResponse],
)
async def cancelar_contrato(
    contrato_id: UUID,
    motivo: str,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Cancela contrato de honorários."""
    try:
        service = HonorarioService(db, escritorio_id)
        contrato = await service.cancelar_contrato(contrato_id, motivo)
        
        return APIResponse(
            success=True,
            data=ContratoResponse.model_validate(contrato),
            message="Contrato cancelado",
        )
    except (ResourceNotFoundError, BusinessRuleError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# === PARCELAS ===


@router.post("/parcelas", response_model=APIResponse[ParcelaResponse])
async def criar_parcela(
    dados: ParcelaCreate,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Cria nova parcela para contrato."""
    try:
        service = HonorarioService(db, escritorio_id)
        parcela = await service.criar_parcela(dados)
        
        return APIResponse(
            success=True,
            data=ParcelaResponse.model_validate(parcela),
            message="Parcela criada",
        )
    except (ResourceNotFoundError, BusinessRuleError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/contratos/{contrato_id}/parcelas",
    response_model=APIResponse[list[ParcelaResponse]],
)
async def listar_parcelas_contrato(
    contrato_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Lista parcelas de um contrato."""
    service = HonorarioService(db, escritorio_id)
    parcelas = await service.listar_parcelas_contrato(contrato_id)
    
    return APIResponse(
        success=True,
        data=[ParcelaResponse.model_validate(p) for p in parcelas],
    )


@router.get(
    "/parcelas/vencidas",
    response_model=APIResponse[list[ParcelaResponse]],
)
async def listar_parcelas_vencidas(
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Lista parcelas vencidas não pagas."""
    service = HonorarioService(db, escritorio_id)
    parcelas = await service.listar_parcelas_vencidas()
    
    return APIResponse(
        success=True,
        data=[ParcelaResponse.model_validate(p) for p in parcelas],
    )


@router.get(
    "/parcelas/a-vencer",
    response_model=APIResponse[list[ParcelaResponse]],
)
async def listar_parcelas_a_vencer(
    db: DBSession,
    escritorio_id: EscritorioID,
    dias: int = Query(30, ge=1, le=365),
):
    """Lista parcelas que vencem nos próximos X dias."""
    service = HonorarioService(db, escritorio_id)
    parcelas = await service.listar_parcelas_a_vencer(dias)
    
    return APIResponse(
        success=True,
        data=[ParcelaResponse.model_validate(p) for p in parcelas],
    )


@router.post(
    "/parcelas/{parcela_id}/pagar",
    response_model=APIResponse[ParcelaResponse],
)
async def registrar_pagamento(
    parcela_id: UUID,
    dados: ParcelaRegistrarPagamento,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Registra pagamento de uma parcela."""
    try:
        service = HonorarioService(db, escritorio_id)
        parcela = await service.registrar_pagamento(parcela_id, dados)
        
        return APIResponse(
            success=True,
            data=ParcelaResponse.model_validate(parcela),
            message="Pagamento registrado",
        )
    except (ResourceNotFoundError, BusinessRuleError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/parcelas/{parcela_id}/cancelar",
    response_model=APIResponse[ParcelaResponse],
)
async def cancelar_parcela(
    parcela_id: UUID,
    motivo: str,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Cancela uma parcela."""
    try:
        service = HonorarioService(db, escritorio_id)
        parcela = await service.cancelar_parcela(parcela_id, motivo)
        
        return APIResponse(
            success=True,
            data=ParcelaResponse.model_validate(parcela),
            message="Parcela cancelada",
        )
    except (ResourceNotFoundError, BusinessRuleError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# === DASHBOARD FINANCEIRO ===


@router.get("/dashboard", response_model=APIResponse[DashboardFinanceiro])
async def get_dashboard_financeiro(
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Retorna dashboard financeiro do escritório."""
    service = HonorarioService(db, escritorio_id)
    dashboard = await service.get_dashboard_financeiro()
    
    return APIResponse(success=True, data=dashboard)


@router.get(
    "/clientes/{cliente_id}/resumo",
    response_model=APIResponse[ResumoFinanceiro],
)
async def get_resumo_financeiro_cliente(
    cliente_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Retorna resumo financeiro de um cliente."""
    service = HonorarioService(db, escritorio_id)
    resumo = await service.get_resumo_financeiro_cliente(cliente_id)
    
    return APIResponse(success=True, data=resumo)
