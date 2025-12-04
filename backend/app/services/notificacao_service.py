"""
Service de Notificações.

Gerencia criação, envio e preferências de notificações.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ResourceNotFoundError
from app.models.notificacao import (
    CanalNotificacao,
    Notificacao,
    PreferenciaNotificacao,
    StatusNotificacao,
    TipoNotificacao,
)
from app.repositories.notificacao_repository import (
    NotificacaoRepository,
    PreferenciaNotificacaoRepository,
)
from app.schemas.notificacao import (
    NotificacaoCreate,
    NotificacaoStats,
    PreferenciaNotificacaoUpdate,
)

logger = structlog.get_logger()


class NotificacaoService:
    """
    Service para gestão de notificações.
    
    Suporta múltiplos canais: Push (FCM), Email, SMS, In-App.
    """
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        self._db = db
        self._escritorio_id = escritorio_id
        self._repo = NotificacaoRepository(db, escritorio_id)
        self._prefs_repo = PreferenciaNotificacaoRepository(db, escritorio_id)
    
    # === NOTIFICAÇÕES ===
    
    async def criar_notificacao(
        self,
        dados: NotificacaoCreate,
        usuario_id: UUID,
    ) -> Notificacao:
        """Cria nova notificação."""
        notificacao = await self._repo.create(
            usuario_id=usuario_id,
            **dados.model_dump(),
        )
        
        logger.info(
            "Notificação criada",
            notificacao_id=str(notificacao.id),
            tipo=dados.tipo.value,
            usuario_id=str(usuario_id),
        )
        
        return notificacao
    
    async def criar_notificacao_prazo(
        self,
        usuario_id: UUID,
        prazo_id: UUID,
        processo_numero: str,
        descricao_prazo: str,
        data_fatal: datetime,
        dias_restantes: int,
    ) -> Notificacao:
        """
        Cria notificação de prazo automaticamente.
        
        Determina tipo baseado nos dias restantes.
        """
        if dias_restantes <= 0:
            tipo = TipoNotificacao.PRAZO_VENCIDO
            titulo = "⚠️ PRAZO VENCIDO"
            prioridade = 10
        elif dias_restantes == 0:
            tipo = TipoNotificacao.PRAZO_HOJE
            titulo = "⚡ PRAZO PARA HOJE"
            prioridade = 9
        elif dias_restantes <= 3:
            tipo = TipoNotificacao.PRAZO_URGENTE
            titulo = f"🔴 PRAZO URGENTE - {dias_restantes} dia(s)"
            prioridade = 8
        else:
            tipo = TipoNotificacao.PRAZO_VENCENDO
            titulo = f"📅 Prazo em {dias_restantes} dias"
            prioridade = 5
        
        dados = NotificacaoCreate(
            tipo=tipo,
            titulo=titulo,
            mensagem=f"Processo {processo_numero}: {descricao_prazo}",
            prioridade=prioridade,
            dados_extras={
                "prazo_id": str(prazo_id),
                "processo_numero": processo_numero,
                "data_fatal": data_fatal.isoformat(),
            },
        )
        
        return await self.criar_notificacao(dados, usuario_id)
    
    async def listar_notificacoes_usuario(
        self,
        usuario_id: UUID,
        apenas_nao_lidas: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notificacao]:
        """Lista notificações de um usuário."""
        return await self._repo.get_by_usuario(
            usuario_id,
            apenas_nao_lidas,
            skip,
            limit,
        )
    
    async def contar_nao_lidas(self, usuario_id: UUID) -> int:
        """Conta notificações não lidas."""
        return await self._repo.count_nao_lidas(usuario_id)
    
    async def marcar_como_lida(self, notificacao_id: UUID) -> Notificacao:
        """Marca notificação como lida."""
        notificacao = await self._repo.marcar_como_lida(notificacao_id)
        
        if not notificacao:
            raise ResourceNotFoundError("Notificação", notificacao_id)
        
        return notificacao
    
    async def marcar_todas_como_lidas(self, usuario_id: UUID) -> int:
        """Marca todas as notificações do usuário como lidas."""
        notificacoes = await self._repo.get_by_usuario(
            usuario_id,
            apenas_nao_lidas=True,
        )
        
        count = 0
        for notif in notificacoes:
            await self._repo.marcar_como_lida(notif.id)
            count += 1
        
        logger.info(
            "Notificações marcadas como lidas",
            usuario_id=str(usuario_id),
            count=count,
        )
        
        return count
    
    async def get_stats(self, usuario_id: UUID) -> NotificacaoStats:
        """Retorna estatísticas de notificações."""
        return await self._repo.get_stats(usuario_id)
    
    # === ENVIO DE NOTIFICAÇÕES ===
    
    async def processar_pendentes(self) -> int:
        """
        Processa e envia notificações pendentes.
        
        Chamado por job agendado (Cloud Tasks/Celery).
        """
        pendentes = await self._repo.get_pendentes_envio()
        count = 0
        
        for notificacao in pendentes:
            try:
                await self._enviar_notificacao(notificacao)
                count += 1
            except Exception as e:
                logger.error(
                    "Erro ao enviar notificação",
                    notificacao_id=str(notificacao.id),
                    error=str(e),
                )
                await self._repo.update(
                    notificacao.id,
                    status=StatusNotificacao.FALHA,
                )
        
        logger.info(
            "Notificações processadas",
            total_pendentes=len(pendentes),
            enviadas=count,
        )
        
        return count
    
    async def _enviar_notificacao(self, notificacao: Notificacao) -> None:
        """Envia notificação pelo canal configurado."""
        # Busca preferências do usuário
        prefs = await self._prefs_repo.get_by_usuario(notificacao.usuario_id)
        
        if not prefs:
            # Usa padrão: in-app
            await self._enviar_in_app(notificacao)
            return
        
        # Verifica se tipo está ativo nas preferências
        if not self._tipo_ativo(notificacao.tipo, prefs):
            await self._repo.update(
                notificacao.id,
                status=StatusNotificacao.ENVIADA,
                enviada_em=datetime.now(timezone.utc),
            )
            return
        
        # Envia pelos canais ativos
        canais_ativos = prefs.canais_ativos or [CanalNotificacao.IN_APP]
        
        for canal in canais_ativos:
            try:
                if canal == CanalNotificacao.PUSH and prefs.fcm_token:
                    await self._enviar_push(notificacao, prefs.fcm_token)
                elif canal == CanalNotificacao.EMAIL:
                    await self._enviar_email(notificacao)
                elif canal == CanalNotificacao.SMS:
                    await self._enviar_sms(notificacao)
                elif canal == CanalNotificacao.IN_APP:
                    await self._enviar_in_app(notificacao)
            except Exception as e:
                logger.error(
                    "Erro ao enviar por canal",
                    canal=canal.value,
                    notificacao_id=str(notificacao.id),
                    error=str(e),
                )
        
        await self._repo.update(
            notificacao.id,
            status=StatusNotificacao.ENVIADA,
            enviada_em=datetime.now(timezone.utc),
        )
    
    async def _enviar_push(self, notificacao: Notificacao, fcm_token: str) -> None:
        """Envia push notification via Firebase Cloud Messaging."""
        # TODO: Implementar integração com FCM
        logger.info(
            "Push notification enviada",
            notificacao_id=str(notificacao.id),
            token_prefix=fcm_token[:20] + "...",
        )
    
    async def _enviar_email(self, notificacao: Notificacao) -> None:
        """Envia notificação por email."""
        # TODO: Implementar envio de email (SendGrid/Mailgun)
        logger.info(
            "Email notification enviada",
            notificacao_id=str(notificacao.id),
        )
    
    async def _enviar_sms(self, notificacao: Notificacao) -> None:
        """Envia notificação por SMS."""
        # TODO: Implementar envio de SMS (Twilio)
        logger.info(
            "SMS notification enviada",
            notificacao_id=str(notificacao.id),
        )
    
    async def _enviar_in_app(self, notificacao: Notificacao) -> None:
        """Marca como disponível para exibição in-app."""
        # Notificações in-app já estão disponíveis após criação
        logger.info(
            "In-app notification disponível",
            notificacao_id=str(notificacao.id),
        )
    
    def _tipo_ativo(
        self,
        tipo: TipoNotificacao,
        prefs: PreferenciaNotificacao,
    ) -> bool:
        """Verifica se tipo de notificação está ativo nas preferências."""
        if prefs.tipos_ativos is None:
            return True  # Todos ativos por padrão
        
        return tipo in prefs.tipos_ativos
    
    # === PREFERÊNCIAS ===
    
    async def get_preferencias(self, usuario_id: UUID) -> PreferenciaNotificacao | None:
        """Busca preferências de notificação do usuário."""
        return await self._prefs_repo.get_by_usuario(usuario_id)
    
    async def atualizar_preferencias(
        self,
        usuario_id: UUID,
        dados: PreferenciaNotificacaoUpdate,
    ) -> PreferenciaNotificacao:
        """Atualiza preferências de notificação."""
        prefs = await self._prefs_repo.get_by_usuario(usuario_id)
        
        if prefs:
            prefs = await self._prefs_repo.update(
                prefs.id,
                **dados.model_dump(exclude_unset=True),
            )
        else:
            prefs = await self._prefs_repo.create(
                usuario_id=usuario_id,
                **dados.model_dump(exclude_unset=True),
            )
        
        logger.info(
            "Preferências de notificação atualizadas",
            usuario_id=str(usuario_id),
        )
        
        return prefs
    
    async def atualizar_fcm_token(
        self,
        usuario_id: UUID,
        fcm_token: str,
    ) -> PreferenciaNotificacao:
        """Atualiza token FCM para push notifications."""
        prefs = await self._prefs_repo.get_by_usuario(usuario_id)
        
        if prefs:
            prefs = await self._prefs_repo.update(prefs.id, fcm_token=fcm_token)
        else:
            prefs = await self._prefs_repo.create(
                usuario_id=usuario_id,
                fcm_token=fcm_token,
            )
        
        return prefs


# === FUNÇÕES AUXILIARES PARA JOBS ===

async def verificar_prazos_e_notificar(
    db: AsyncSession,
    escritorio_id: UUID,
) -> int:
    """
    Verifica prazos próximos e cria notificações.
    
    Chamado por job diário.
    """
    from app.services.processo_service import ProcessoService
    
    processo_service = ProcessoService(db, escritorio_id)
    notif_service = NotificacaoService(db, escritorio_id)
    
    # Busca prazos urgentes (próximos X dias)
    dias_antes = settings.NOTIFICATION_DAYS_BEFORE_DEADLINE or 7
    prazos_urgentes = await processo_service.listar_prazos_pendentes(dias_antes)
    
    notificacoes_criadas = 0
    
    for prazo in prazos_urgentes:
        # Cria notificação para responsável
        if prazo.responsavel_id:
            await notif_service.criar_notificacao_prazo(
                usuario_id=prazo.responsavel_id,
                prazo_id=prazo.id,
                processo_numero=prazo.processo.numero_principal,
                descricao_prazo=prazo.descricao,
                data_fatal=prazo.data_fatal,
                dias_restantes=prazo.dias_restantes,
            )
            notificacoes_criadas += 1
    
    logger.info(
        "Verificação de prazos concluída",
        prazos_verificados=len(prazos_urgentes),
        notificacoes_criadas=notificacoes_criadas,
    )
    
    return notificacoes_criadas
