"""
Middleware de tratamento de exceções.

Converte exceções em respostas HTTP padronizadas.
"""

import traceback
from typing import Callable

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    AIServiceError,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    CRMException,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    StorageError,
    TokenExpiredError,
    ValidationError,
)

logger = structlog.get_logger()


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    """Cria resposta de erro padronizada."""
    content = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details and settings.DEBUG:
        content["error"]["details"] = details
    
    return JSONResponse(status_code=status_code, content=content)


async def crm_exception_handler(request: Request, exc: CRMException) -> JSONResponse:
    """Handler para exceções do CRM."""
    logger.warning(
        "CRM exception",
        code=exc.code,
        message=exc.message,
        path=request.url.path,
        details=exc.details,
    )
    
    # Mapeia exceções para status HTTP
    status_map = {
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        TokenExpiredError: status.HTTP_401_UNAUTHORIZED,
        AuthorizationError: status.HTTP_403_FORBIDDEN,
        ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
        ResourceAlreadyExistsError: status.HTTP_409_CONFLICT,
        ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        BusinessRuleError: status.HTTP_400_BAD_REQUEST,
        StorageError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        AIServiceError: status.HTTP_503_SERVICE_UNAVAILABLE,
    }
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    for exc_type, http_status in status_map.items():
        if isinstance(exc, exc_type):
            status_code = http_status
            break
    
    return create_error_response(
        status_code=status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler para exceções não tratadas."""
    logger.error(
        "Unhandled exception",
        exc_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path,
        traceback=traceback.format_exc() if settings.DEBUG else None,
    )
    
    message = "Erro interno do servidor"
    details = None
    
    if settings.DEBUG:
        message = str(exc)
        details = {"traceback": traceback.format_exc()}
    
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        message=message,
        details=details,
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Registra handlers de exceção na aplicação."""
    app.add_exception_handler(CRMException, crm_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


class RequestContextMiddleware:
    """
    Middleware para adicionar contexto às requisições.
    
    Adiciona request_id e informações do usuário ao contexto de log.
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        import uuid
        
        request_id = str(uuid.uuid4())[:8]
        
        # Bind request context to structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=scope.get("path", ""),
            method=scope.get("method", ""),
        )
        
        # Add request_id header to response
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
