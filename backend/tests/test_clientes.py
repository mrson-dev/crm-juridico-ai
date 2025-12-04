"""
Testes para o endpoint de clientes.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.models.cliente import Cliente


@pytest.mark.asyncio
async def test_list_clientes_empty(client: AsyncClient):
    """Testa listagem de clientes vazia."""
    response = await client.get("/api/v1/clientes")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_cliente(client: AsyncClient):
    """Testa criação de cliente."""
    cliente_data = {
        "cpf": "123.456.789-01",
        "nome": "João da Silva",
        "email": "joao@email.com",
        "telefone": "11999999999",
        "consentimento_lgpd": True,
    }
    
    response = await client.post("/api/v1/clientes", json=cliente_data)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["nome"] == "João da Silva"
    assert data["data"]["cpf"] == "123.456.789-01"
    assert "id" in data["data"]


@pytest.mark.asyncio
async def test_create_cliente_invalid_cpf(client: AsyncClient):
    """Testa criação de cliente com CPF inválido."""
    cliente_data = {
        "cpf": "123",  # CPF inválido
        "nome": "João da Silva",
        "consentimento_lgpd": True,
    }
    
    response = await client.post("/api/v1/clientes", json=cliente_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_cliente_not_found(client: AsyncClient):
    """Testa busca de cliente inexistente."""
    fake_id = uuid4()
    response = await client.get(f"/api/v1/clientes/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_clientes(client: AsyncClient):
    """Testa busca de clientes."""
    # Primeiro cria um cliente
    cliente_data = {
        "cpf": "987.654.321-00",
        "nome": "Maria Oliveira",
        "consentimento_lgpd": True,
    }
    await client.post("/api/v1/clientes", json=cliente_data)
    
    # Busca por nome
    response = await client.get("/api/v1/clientes?search=Maria")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any("Maria" in c["nome"] for c in data["data"])
