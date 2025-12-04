"""
Router principal da API v1.

Agrega todas as rotas organizadas por domínio.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    clientes,
    documentos,
    health,
    honorarios,
    notificacoes,
    processos,
)

api_router = APIRouter()

# Health check
api_router.include_router(health.router, prefix="/health", tags=["Health"])

# Autenticação
api_router.include_router(auth.router)

# Clientes
api_router.include_router(clientes.router)

# Processos, Prazos e Andamentos
api_router.include_router(processos.router)

# Documentos e IA
api_router.include_router(documentos.router)

# Notificações
api_router.include_router(notificacoes.router)

# Honorários e Financeiro
api_router.include_router(honorarios.router)
