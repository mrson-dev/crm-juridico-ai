"""
Endpoints de Notificações.

Rotas para gerenciamento de notificações e preferências.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DBSession, EscritorioID
from app.core.exceptions import ResourceNotFoundError
from app.schemas.base import APIResponse
from app.schemas.notificacao import (
    NotificacaoCreate,
    NotificacaoResponse,
    NotificacaoStats,
    PreferenciaNotificacaoResponse,
    PreferenciaNotificacaoUpdate,
)
from app.services.notificacao_service import NotificacaoService

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get("", response_model=APIResponse[list[NotificacaoResponse]])
async def listar_notificacoes(
    db: DBSession,
    escritorio_id: EscritorioID,
    current_user: CurrentUser,
    apenas_nao_lidas: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Lista notificações do usuário autenticado."""
    service = NotificacaoService(db, escritorio_id)
    notificacoes = await service.listar_notificacoes_usuario(
        current_user.id,
        apenas_nao_lidas,
        skip,
        limit,
    )
    
    return APIResponse(
        success=True,
        data=[NotificacaoResponse.model_validate(n) for n in notificacoes],
    )


@router.get("/count", response_model=APIResponse[int])
async def contar_nao_lidas(
    db: DBSession,
    escritorio_id: EscritorioID,
    current_user: CurrentUser,
):
    """Conta notificações não lidas."""
    service = NotificacaoService(db, escritorio_id)
    count = await service.contar_nao_lidas(current_user.id)
    
    return APIResponse(success=True, data=count)


@router.get("/stats", response_model=APIResponse[NotificacaoStats])
async def get_stats(
    db: DBSession,
    escritorio_id: EscritorioID,
    current_user: CurrentUser,
):
    """Retorna estatísticas de notificações."""
    service = NotificacaoService(db, escritorio_id)
    stats = await service.get_stats(current_user.id)
    
    return APIResponse(success=True, data=stats)


@router.post("/{notificacao_id}/lida", response_model=APIResponse[NotificacaoResponse])
async def marcar_como_lida(
    notificacao_id: UUID,
    db: DBSession,
    escritorio_id: EscritorioID,
):
    """Marca notificação como lida."""
    try:
        service = NotificacaoService(db, escritorio_id)
        notificacao = await service.marcar_como_lida(notificacao_id)
        
        return APIResponse(
            success=True,
            data=NotificacaoResponse.model_validate(notificacao),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/marcar-todas-lidas", response_model=APIResponse[int])
async def marcar_todas_como_lidas(
    db: DBSession,
    escritorio_id: EscritorioID,
    current_user: CurrentUser,
):
    """Marca todas as notificações como lidas."""
    service = NotificacaoService(db, escritorio_id)
    count = await service.marcar_todas_como_lidas(current_user.id)
    
    return APIResponse(
        success=True,
        data=count,
        message=f"{count} notificações marcadas como lidas",
    )


# === PREFERÊNCIAS ===


@router.get(
    "/preferencias",
    response_model=APIResponse[PreferenciaNotificacaoResponse | None],
)
async def get_preferencias(
    db: DBSession,
    escritorio_id: EscritorioID,
    current_user: CurrentUser,
):
    """Busca preferências de notificação do usuário."""
    service = NotificacaoService(db, escritorio_id)
    prefs = await service.get_preferencias(current_user.id)
    
    data = PreferenciaNotificacaoResponse.model_validate(prefs) if prefs else None
    
    return APIResponse(success=True, data=data)


@router.put(
    "/preferencias",
    response_model=APIResponse[PreferenciaNotificacaoResponse],
)
async def atualizar_preferencias(
    dados: PreferenciaNotificacaoUpdate,
    db: DBSession,
    escritorio_id: EscritorioID,
    current_user: CurrentUser,
):
    """Atualiza preferências de notificação."""
    service = NotificacaoService(db, escritorio_id)
    prefs = await service.atualizar_preferencias(current_user.id, dados)
    
    return APIResponse(
        success=True,
        data=PreferenciaNotificacaoResponse.model_validate(prefs),
    )


@router.post("/preferencias/fcm-token", response_model=APIResponse)
async def atualizar_fcm_token(
    fcm_token: str,
    db: DBSession,
    escritorio_id: EscritorioID,
    current_user: CurrentUser,
):
    """Atualiza token FCM para push notifications."""
    service = NotificacaoService(db, escritorio_id)
    await service.atualizar_fcm_token(current_user.id, fcm_token)
    
    return APIResponse(
        success=True,
        message="Token FCM atualizado",
    )
