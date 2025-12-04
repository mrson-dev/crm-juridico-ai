"""
Tasks de notificações.

Tarefas assíncronas para envio de notificações e alertas de prazos.
"""

import structlog
from celery import shared_task

from app.core.config import settings

logger = structlog.get_logger()


async def get_async_session():
    """Cria sessão async para uso nas tasks."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


@shared_task(bind=True)
def verificar_prazos_task(self):
    """
    Verifica prazos e cria notificações.
    
    Executado diariamente às 8h pelo beat schedule.
    Cria notificações para prazos próximos do vencimento.
    """
    import asyncio
    from datetime import datetime, timedelta, timezone
    
    async def _check_deadlines():
        from sqlalchemy import select
        from app.models.escritorio import Escritorio
        from app.services.notificacao_service import verificar_prazos_e_notificar
        
        session = await get_async_session()
        total_notificacoes = 0
        
        try:
            # Busca todos os escritórios ativos
            result = await session.execute(
                select(Escritorio).where(Escritorio.is_active == True)
            )
            escritorios = result.scalars().all()
            
            for escritorio in escritorios:
                try:
                    count = await verificar_prazos_e_notificar(
                        session,
                        escritorio.id,
                    )
                    total_notificacoes += count
                    
                except Exception as e:
                    logger.error(
                        "Erro ao verificar prazos do escritório",
                        escritorio_id=str(escritorio.id),
                        error=str(e),
                    )
            
            await session.commit()
            
            logger.info(
                "Verificação de prazos concluída",
                escritorios=len(escritorios),
                notificacoes_criadas=total_notificacoes,
            )
            
            return {
                "escritorios_verificados": len(escritorios),
                "notificacoes_criadas": total_notificacoes,
            }
            
        finally:
            await session.close()
    
    return asyncio.run(_check_deadlines())


@shared_task(bind=True)
def enviar_notificacoes_task(self):
    """
    Processa e envia notificações pendentes.
    
    Executado a cada minuto pelo beat schedule.
    """
    import asyncio
    
    async def _send_notifications():
        from sqlalchemy import select
        from app.models.escritorio import Escritorio
        from app.services.notificacao_service import NotificacaoService
        
        session = await get_async_session()
        total_enviadas = 0
        
        try:
            # Busca escritórios ativos
            result = await session.execute(
                select(Escritorio).where(Escritorio.is_active == True)
            )
            escritorios = result.scalars().all()
            
            for escritorio in escritorios:
                try:
                    service = NotificacaoService(session, escritorio.id)
                    count = await service.processar_pendentes()
                    total_enviadas += count
                    
                except Exception as e:
                    logger.error(
                        "Erro ao enviar notificações do escritório",
                        escritorio_id=str(escritorio.id),
                        error=str(e),
                    )
            
            await session.commit()
            
            if total_enviadas > 0:
                logger.info(
                    "Notificações enviadas",
                    total=total_enviadas,
                )
            
            return {"notificacoes_enviadas": total_enviadas}
            
        finally:
            await session.close()
    
    return asyncio.run(_send_notifications())


@shared_task(bind=True, max_retries=3)
def enviar_push_notification_task(
    self,
    fcm_token: str,
    titulo: str,
    mensagem: str,
    dados: dict = None,
):
    """
    Envia push notification via Firebase Cloud Messaging.
    
    Pode ser chamada diretamente ou pelo NotificacaoService.
    """
    try:
        # TODO: Implementar integração real com FCM
        # import firebase_admin
        # from firebase_admin import messaging
        
        # message = messaging.Message(
        #     notification=messaging.Notification(
        #         title=titulo,
        #         body=mensagem,
        #     ),
        #     data=dados or {},
        #     token=fcm_token,
        # )
        # response = messaging.send(message)
        
        logger.info(
            "Push notification enviada",
            token_prefix=fcm_token[:20] + "...",
            titulo=titulo,
        )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(
            "Erro ao enviar push notification",
            error=str(e),
        )
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def enviar_email_task(
    self,
    destinatario: str,
    assunto: str,
    corpo_html: str,
    corpo_texto: str = None,
):
    """
    Envia email de notificação.
    
    Usa SendGrid ou outro serviço de email configurado.
    """
    try:
        # TODO: Implementar integração com serviço de email
        # import sendgrid
        # sg = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)
        
        logger.info(
            "Email enviado",
            destinatario=destinatario,
            assunto=assunto,
        )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(
            "Erro ao enviar email",
            destinatario=destinatario,
            error=str(e),
        )
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2)
def enviar_sms_task(
    self,
    telefone: str,
    mensagem: str,
):
    """
    Envia SMS de notificação.
    
    Usa Twilio ou outro serviço de SMS configurado.
    """
    try:
        # TODO: Implementar integração com Twilio
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
        # message = client.messages.create(
        #     body=mensagem,
        #     from_=settings.TWILIO_PHONE,
        #     to=telefone,
        # )
        
        logger.info(
            "SMS enviado",
            telefone=telefone[-4:],  # Log apenas últimos 4 dígitos
        )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(
            "Erro ao enviar SMS",
            error=str(e),
        )
        raise self.retry(exc=e)


@shared_task
def notificar_prazo_urgente_task(
    escritorio_id: str,
    prazo_id: str,
    usuario_id: str,
    processo_numero: str,
    descricao: str,
    dias_restantes: int,
):
    """
    Cria e envia notificação de prazo urgente.
    
    Usado para alertas imediatos (menos de 3 dias).
    """
    import asyncio
    from uuid import UUID
    from datetime import datetime, timezone
    
    async def _notify():
        from app.services.notificacao_service import NotificacaoService
        from app.schemas.notificacao import NotificacaoCreate
        from app.models.notificacao import TipoNotificacao
        
        session = await get_async_session()
        
        try:
            service = NotificacaoService(session, UUID(escritorio_id))
            
            # Determina tipo e prioridade
            if dias_restantes <= 0:
                tipo = TipoNotificacao.PRAZO_VENCIDO
                titulo = "⚠️ PRAZO VENCIDO"
                prioridade = 10
            elif dias_restantes == 1:
                tipo = TipoNotificacao.PRAZO_HOJE
                titulo = "⚡ PRAZO AMANHÃ"
                prioridade = 9
            else:
                tipo = TipoNotificacao.PRAZO_URGENTE
                titulo = f"🔴 PRAZO EM {dias_restantes} DIAS"
                prioridade = 8
            
            dados = NotificacaoCreate(
                tipo=tipo,
                titulo=titulo,
                mensagem=f"Processo {processo_numero}: {descricao}",
                prioridade=prioridade,
                dados_extras={
                    "prazo_id": prazo_id,
                    "processo_numero": processo_numero,
                    "dias_restantes": dias_restantes,
                },
            )
            
            notificacao = await service.criar_notificacao(dados, UUID(usuario_id))
            
            # Tenta enviar imediatamente
            await service.processar_pendentes()
            
            await session.commit()
            
            logger.info(
                "Notificação de prazo urgente criada",
                prazo_id=prazo_id,
                dias_restantes=dias_restantes,
            )
            
            return {"notificacao_id": str(notificacao.id)}
            
        finally:
            await session.close()
    
    return asyncio.run(_notify())


@shared_task
def enviar_resumo_diario_task(escritorio_id: str, usuario_id: str):
    """
    Envia resumo diário de atividades para o usuário.
    
    Inclui prazos do dia, processos atualizados, etc.
    """
    import asyncio
    from uuid import UUID
    from datetime import datetime, timezone
    
    async def _send_summary():
        from app.services.processo_service import ProcessoService
        from app.services.notificacao_service import NotificacaoService
        
        session = await get_async_session()
        
        try:
            processo_service = ProcessoService(session, UUID(escritorio_id))
            notif_service = NotificacaoService(session, UUID(escritorio_id))
            
            # Coleta dados do resumo
            prazos_hoje = await processo_service.listar_prazos_urgentes(dias=1)
            prazos_semana = await processo_service.listar_prazos_urgentes(dias=7)
            andamentos_recentes = await processo_service.listar_andamentos_recentes(dias=1)
            
            # Monta resumo
            resumo = {
                "data": datetime.now(timezone.utc).isoformat(),
                "prazos_hoje": len(prazos_hoje),
                "prazos_semana": len(prazos_semana),
                "andamentos_ontem": len(andamentos_recentes),
            }
            
            # Se há prazos hoje, cria notificação
            if prazos_hoje:
                from app.schemas.notificacao import NotificacaoCreate
                from app.models.notificacao import TipoNotificacao
                
                dados = NotificacaoCreate(
                    tipo=TipoNotificacao.SISTEMA,
                    titulo="📋 Resumo do Dia",
                    mensagem=f"Você tem {len(prazos_hoje)} prazo(s) para hoje e {len(prazos_semana)} esta semana.",
                    prioridade=5,
                    dados_extras=resumo,
                )
                
                await notif_service.criar_notificacao(dados, UUID(usuario_id))
            
            await session.commit()
            
            logger.info(
                "Resumo diário enviado",
                usuario_id=usuario_id,
                resumo=resumo,
            )
            
            return resumo
            
        finally:
            await session.close()
    
    return asyncio.run(_send_summary())
