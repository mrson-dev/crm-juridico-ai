"""
Pytest fixtures para testes do CRM Jurídico AI.
"""
import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.base import Base
from app.core.dependencies import get_db, get_current_user, get_escritorio_id
from app.models.usuario import Usuario, UserRole
from app.models.escritorio import Escritorio
from app.core.security import get_password_hash

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"

# Create test engine with NullPool to avoid connection issues
test_engine = create_async_engine(
    TEST_DATABASE_URL, 
    echo=False,
    poolclass=NullPool,
)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Cria event loop para testes async."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Cria sessão de banco de dados para cada teste."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_escritorio(db_session: AsyncSession) -> Escritorio:
    """Cria escritório de teste."""
    escritorio = Escritorio(
        id=uuid4(),
        nome="Escritório Teste",
        cnpj="12345678000100",
        email="escritorio@teste.com",
    )
    db_session.add(escritorio)
    await db_session.commit()
    await db_session.refresh(escritorio)
    return escritorio


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_escritorio: Escritorio) -> Usuario:
    """Cria usuário de teste."""
    user = Usuario(
        id=uuid4(),
        email="test@example.com",
        nome="Usuário Teste",
        hashed_password=get_password_hash("password123"),
        role=UserRole.ADMIN,
        escritorio_id=test_escritorio.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    test_user: Usuario,
    test_escritorio: Escritorio,
) -> AsyncGenerator[AsyncClient, None]:
    """Cria cliente HTTP autenticado para testes."""
    
    async def override_get_db():
        yield db_session
    
    async def override_get_current_user():
        return test_user
    
    async def override_get_escritorio_id():
        return test_escritorio.id
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_escritorio_id] = override_get_escritorio_id
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthenticated_client() -> AsyncGenerator[AsyncClient, None]:
    """Cria cliente HTTP sem autenticação."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
