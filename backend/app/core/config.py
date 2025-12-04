"""
Configurações da aplicação usando Pydantic Settings.

Carrega variáveis de ambiente e valida configurações necessárias.
"""

from functools import lru_cache
from typing import Any

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais da aplicação."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Aplicação
    PROJECT_NAME: str = "CRM Jurídico API"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # Segurança
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas
    ALGORITHM: str = "HS256"
    
    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    DATABASE_URL: PostgresDsn | str = "postgresql+asyncpg://postgres:postgres@localhost:5432/crm_juridico"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: Any) -> str:
        """Garante que a URL do banco usa driver asyncpg."""
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return str(v)

    # GCP
    GCP_PROJECT_ID: str = ""
    GCS_BUCKET_DOCUMENTOS: str = ""
    
    # Gemini / Vertex AI
    GEMINI_API_KEY: str = ""
    VERTEX_AI_LOCATION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # Redis (para Celery e cache)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300  # 5 minutos

    # Firebase Authentication
    FIREBASE_CREDENTIALS_PATH: str = ""  # Caminho para service account JSON (dev)
    FIREBASE_PROJECT_ID: str = ""  # Usado em produção com ADC
    
    # Configurações de upload
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_DOCUMENT_TYPES: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    ]

    # Notificações
    NOTIFICATION_DAYS_BEFORE_DEADLINE: list[int] = [7, 3, 1, 0]  # Dias antes do prazo
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"


@lru_cache
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()


settings = get_settings()
