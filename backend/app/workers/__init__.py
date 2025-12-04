"""
Workers para processamento em background.

Módulos:
- celery_app: Configuração do Celery
- document_tasks: Processamento de documentos e OCR
- notification_tasks: Envio de notificações
- calculation_tasks: Cálculos previdenciários
"""

from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
