"""
Integração com Firebase Authentication.

Valida tokens Firebase e sincroniza usuários com o banco local.
"""

from typing import Any

import structlog
from firebase_admin import auth, credentials, initialize_app
from firebase_admin.exceptions import FirebaseError

from app.core.config import settings
from app.core.exceptions import FirebaseAuthError, InvalidTokenError

logger = structlog.get_logger()

# Inicialização do Firebase Admin SDK
_firebase_app = None


def get_firebase_app():
    """Inicializa Firebase Admin SDK sob demanda."""
    global _firebase_app
    
    if _firebase_app is None:
        try:
            # Em produção, usa ADC (Application Default Credentials)
            # Em desenvolvimento, pode usar arquivo de credenciais
            if settings.FIREBASE_CREDENTIALS_PATH:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                _firebase_app = initialize_app(cred)
            else:
                # Usa ADC (recomendado em Cloud Run)
                _firebase_app = initialize_app()
            
            logger.info("Firebase Admin SDK inicializado")
        except Exception as e:
            logger.error("Erro ao inicializar Firebase Admin", error=str(e))
            raise FirebaseAuthError(f"Erro ao inicializar Firebase: {str(e)}")
    
    return _firebase_app


class FirebaseAuthService:
    """
    Serviço de autenticação com Firebase.
    
    Valida tokens ID do Firebase e gerencia usuários.
    """
    
    def __init__(self):
        self._app = None
    
    @property
    def app(self):
        """Inicializa app sob demanda."""
        if self._app is None:
            self._app = get_firebase_app()
        return self._app
    
    async def verify_token(self, id_token: str) -> dict[str, Any]:
        """
        Verifica token ID do Firebase.
        
        Args:
            id_token: Token ID recebido do frontend
        
        Returns:
            Dict com dados do usuário (uid, email, etc.)
        
        Raises:
            InvalidTokenError: Token inválido ou expirado
        """
        try:
            # Força inicialização do app
            _ = self.app
            
            decoded_token = auth.verify_id_token(id_token)
            
            logger.debug(
                "Token Firebase verificado",
                uid=decoded_token.get("uid"),
                email=decoded_token.get("email"),
            )
            
            return decoded_token
            
        except auth.ExpiredIdTokenError:
            logger.warning("Token Firebase expirado")
            raise InvalidTokenError()
        except auth.InvalidIdTokenError as e:
            logger.warning("Token Firebase inválido", error=str(e))
            raise InvalidTokenError()
        except FirebaseError as e:
            logger.error("Erro Firebase", error=str(e))
            raise FirebaseAuthError(str(e))
    
    async def get_user(self, uid: str) -> dict[str, Any]:
        """
        Obtém dados do usuário no Firebase.
        
        Args:
            uid: UID do usuário no Firebase
        
        Returns:
            Dict com dados do usuário
        """
        try:
            _ = self.app
            user = auth.get_user(uid)
            
            return {
                "uid": user.uid,
                "email": user.email,
                "email_verified": user.email_verified,
                "display_name": user.display_name,
                "photo_url": user.photo_url,
                "disabled": user.disabled,
                "provider_data": [
                    {
                        "provider_id": p.provider_id,
                        "uid": p.uid,
                        "email": p.email,
                    }
                    for p in user.provider_data
                ],
            }
            
        except auth.UserNotFoundError:
            logger.warning("Usuário não encontrado no Firebase", uid=uid)
            raise FirebaseAuthError(f"Usuário {uid} não encontrado")
        except FirebaseError as e:
            logger.error("Erro ao buscar usuário Firebase", error=str(e))
            raise FirebaseAuthError(str(e))
    
    async def create_user(
        self,
        email: str,
        password: str,
        display_name: str | None = None,
    ) -> str:
        """
        Cria usuário no Firebase.
        
        Returns:
            UID do novo usuário
        """
        try:
            _ = self.app
            
            user = auth.create_user(
                email=email,
                password=password,
                display_name=display_name,
                email_verified=False,
            )
            
            logger.info("Usuário criado no Firebase", uid=user.uid, email=email)
            return user.uid
            
        except auth.EmailAlreadyExistsError:
            raise FirebaseAuthError(f"Email {email} já está em uso")
        except FirebaseError as e:
            logger.error("Erro ao criar usuário Firebase", error=str(e))
            raise FirebaseAuthError(str(e))
    
    async def update_user(
        self,
        uid: str,
        **kwargs,
    ) -> None:
        """Atualiza dados do usuário no Firebase."""
        try:
            _ = self.app
            auth.update_user(uid, **kwargs)
            logger.info("Usuário atualizado no Firebase", uid=uid)
        except FirebaseError as e:
            logger.error("Erro ao atualizar usuário Firebase", error=str(e))
            raise FirebaseAuthError(str(e))
    
    async def delete_user(self, uid: str) -> None:
        """Remove usuário do Firebase."""
        try:
            _ = self.app
            auth.delete_user(uid)
            logger.info("Usuário removido do Firebase", uid=uid)
        except FirebaseError as e:
            logger.error("Erro ao remover usuário Firebase", error=str(e))
            raise FirebaseAuthError(str(e))
    
    async def set_custom_claims(
        self,
        uid: str,
        claims: dict[str, Any],
    ) -> None:
        """
        Define custom claims no token do usuário.
        
        Útil para passar escritorio_id e roles para o frontend.
        """
        try:
            _ = self.app
            auth.set_custom_user_claims(uid, claims)
            logger.info("Custom claims definidos", uid=uid, claims=claims)
        except FirebaseError as e:
            logger.error("Erro ao definir custom claims", error=str(e))
            raise FirebaseAuthError(str(e))
    
    async def revoke_refresh_tokens(self, uid: str) -> None:
        """Revoga todos os refresh tokens do usuário."""
        try:
            _ = self.app
            auth.revoke_refresh_tokens(uid)
            logger.info("Refresh tokens revogados", uid=uid)
        except FirebaseError as e:
            logger.error("Erro ao revogar tokens", error=str(e))
            raise FirebaseAuthError(str(e))
    
    async def send_password_reset_email(self, email: str) -> str:
        """
        Gera link de reset de senha.
        
        Returns:
            Link para reset de senha
        """
        try:
            _ = self.app
            link = auth.generate_password_reset_link(email)
            logger.info("Link de reset gerado", email=email)
            return link
        except FirebaseError as e:
            logger.error("Erro ao gerar link de reset", error=str(e))
            raise FirebaseAuthError(str(e))


# Singleton para uso global
firebase_auth_service = FirebaseAuthService()
