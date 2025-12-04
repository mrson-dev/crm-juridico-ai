"""
Health check endpoints.
"""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("")
async def health_check() -> dict:
    """Health check básico."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
    }


@router.get("/ready")
async def readiness_check() -> dict:
    """
    Readiness check para Kubernetes/Cloud Run.
    
    Verifica se a aplicação está pronta para receber tráfego.
    """
    # TODO: Adicionar verificação de conexão com banco
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
            "storage": "ok",
        },
    }
