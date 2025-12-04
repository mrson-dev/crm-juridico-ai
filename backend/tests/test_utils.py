"""
Testes para utilitários e helpers.
"""
import pytest
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.base import APIResponse


def test_password_hashing():
    """Testa hash e verificação de senha."""
    password = "my_secure_password"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_create_access_token():
    """Testa criação de token JWT."""
    data = {"sub": "user@example.com", "user_id": "123"}
    token = create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_api_response_model():
    """Testa modelo de resposta da API."""
    response = APIResponse(success=True, data={"key": "value"}, message="OK")
    
    assert response.success is True
    assert response.data == {"key": "value"}
    assert response.message == "OK"
