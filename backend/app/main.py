"""
Ponto de entrada principal da API do CRM Jurídico.

Este módulo configura a aplicação FastAPI com todas as rotas,
middlewares e handlers de eventos.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação."""
    # Startup
    setup_logging()
    logger.info("Iniciando CRM Jurídico API", version=settings.VERSION)
    
    yield
    
    # Shutdown
    logger.info("Encerrando CRM Jurídico API")


def create_application() -> FastAPI:
    """Factory para criar a aplicação FastAPI."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="CRM especializado em Direito Previdenciário com IA integrada",
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rotas
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Endpoint de health check para Cloud Run."""
    return {"status": "healthy", "version": settings.VERSION}
