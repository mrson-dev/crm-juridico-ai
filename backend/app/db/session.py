"""
Configuração da sessão de banco de dados assíncrona.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Engine assíncrona
# NullPool é recomendado para Cloud Run (serverless)
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    poolclass=NullPool,  # Cada request cria sua própria conexão
    future=True,
)

# Session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
