"""
Endpoints de Clientes.

Rotas para gerenciamento de clientes do escritório.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DBSession, EscritorioID
from app.core.exceptions import BusinessRuleError, LGPDConsentRequiredError, ResourceNotFoundError
from app.schemas.base import APIResponse, PaginatedResponse
from app.schemas.cliente import (
    ClienteCreate,
    ClienteListResponse,
    ClienteResponse,
    ClienteUpdate,
)
from app.services.cliente_service import ClienteService

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post(
    "",
    response_model=APIResponse[ClienteResponse],
    status_code=status.HTTP_201_CREATED,
)
async def criar_cliente(
    dados: ClienteCreate,
    db: DBSession,
    escritorio_id: EscritorioID,
) -> APIResponse[ClienteResponse]:
    """
    Cria novo cliente.
    
    Requer consentimento LGPD (consentimento_lgpd=true).
    """
    try:
        service = ClienteService(db, escritorio_id)
        cliente = await service.criar(dados)
        
        return APIResponse(
            success=True,
            data=ClienteResponse.model_validate(cliente),
            message="Cliente criado com sucesso",
        )
    except LGPDConsentRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=PaginatedResponse[ClienteListResponse])
async def listar_clientes(
    db: DBSession,
    escritorio_id: EscritorioID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    apenas_ativos: bool = Query(True),
) -> PaginatedResponse[ClienteListResponse]:
    """Lista clientes do escritório com paginação."""
    service = ClienteService(db, escritorio_id)
    clientes = await service.listar(skip, limit, apenas_ativos)
    
    return PaginatedResponse(
        success=True,
        data=[ClienteListResponse.model_validate(c) for c in clientes],
        total=len(clientes),
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get("/search", response_model=APIResponse[list[ClienteListResponse]])
async def pesquisar_clientes(
    db: DBSession,
    escritorio_id: EscritorioID,
    q: str = Query(..., min_length=2, description="Termo de busca"),
) -> APIResponse[list[ClienteListResponse]]:
    """Pesquisa clientes por nome, CPF ou email."""
    service = ClienteService(db, escritorio_id)
    clientes = await service.pesquisar(q)
    
    return APIResponse(
        success=True,
        data=[ClienteListResponse.model_validate(c) for c in clientes],
    )


@router.get("/{cliente_id}", response_model=APIResponse[ClienteResponse])
async def obter_cliente(
    cliente_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
) -> APIResponse[ClienteResponse]:
    """Obtém detalhes de um cliente específico."""
    try:
        service = ClienteService(db, escritorio_id)
        cliente = await service.buscar_por_id(cliente_id)
        
        if not cliente:
            raise ResourceNotFoundError("Cliente", cliente_id)
        
        return APIResponse(success=True, data=ClienteResponse.model_validate(cliente))
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{cliente_id}", response_model=APIResponse[ClienteResponse])
async def atualizar_cliente(
    cliente_id: UUID,
    dados: ClienteUpdate,
    db: DBSession,
    escritorio_id: EscritorioID,
) -> APIResponse[ClienteResponse]:
    """Atualiza dados de um cliente."""
    service = ClienteService(db, escritorio_id)
    cliente = await service.atualizar(cliente_id, dados)
    
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    
    return APIResponse(success=True, data=ClienteResponse.model_validate(cliente))


@router.delete("/{cliente_id}", response_model=APIResponse)
async def desativar_cliente(
    cliente_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
) -> APIResponse:
    """Desativa um cliente (soft delete - LGPD compliance)."""
    service = ClienteService(db, escritorio_id)
    cliente = await service.desativar(cliente_id)
    
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    
    return APIResponse(success=True, message="Cliente desativado com sucesso")
