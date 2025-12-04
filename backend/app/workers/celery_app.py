"""
Configuração do Celery.

Worker para processamento assíncrono de tarefas.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "crm-juridico",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.document_tasks",
        "app.workers.notification_tasks",
        "app.workers.calculation_tasks",
    ],
)

# Configurações do Celery
celery_app.conf.update(
    # Timezone
    timezone="America/Sao_Paulo",
    enable_utc=True,
    
    # Serialização
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Tarefas
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutos max
    task_soft_time_limit=25 * 60,  # 25 minutos soft limit
    
    # Retries
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Concorrência
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    
    # Resultados
    result_expires=60 * 60 * 24,  # 24 horas
    
    # Beat Schedule (tarefas agendadas)
    beat_schedule={
        # Verifica prazos todo dia às 8h
        "verificar-prazos-diario": {
            "task": "app.workers.notification_tasks.verificar_prazos_task",
            "schedule": {
                "hour": 8,
                "minute": 0,
            },
        },
        # Processa documentos pendentes a cada 5 minutos
        "processar-documentos-pendentes": {
            "task": "app.workers.document_tasks.processar_documentos_pendentes_task",
            "schedule": 300.0,  # 5 minutos
        },
        # Envia notificações pendentes a cada minuto
        "enviar-notificacoes-pendentes": {
            "task": "app.workers.notification_tasks.enviar_notificacoes_task",
            "schedule": 60.0,  # 1 minuto
        },
    },
)

# Para execução local: celery -A app.workers.celery_app worker --loglevel=info
# Para beat: celery -A app.workers.celery_app beat --loglevel=info
