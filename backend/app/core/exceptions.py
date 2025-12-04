"""
Exceções customizadas da aplicação.

Define hierarquia de exceções para tratamento consistente de erros.
"""

from typing import Any
from uuid import UUID


class CRMException(Exception):
    """Exceção base do CRM Jurídico."""
    
    def __init__(
        self,
        message: str,
        code: str = "CRM_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


# === Exceções de Autenticação ===

class AuthenticationError(CRMException):
    """Erro de autenticação."""
    
    def __init__(self, message: str = "Credenciais inválidas"):
        super().__init__(message, code="AUTH_ERROR")


class TokenExpiredError(AuthenticationError):
    """Token JWT expirado."""
    
    def __init__(self):
        super().__init__("Token expirado")
        self.code = "TOKEN_EXPIRED"


class InvalidTokenError(AuthenticationError):
    """Token JWT inválido."""
    
    def __init__(self):
        super().__init__("Token inválido")
        self.code = "INVALID_TOKEN"


class FirebaseAuthError(AuthenticationError):
    """Erro de autenticação Firebase."""
    
    def __init__(self, message: str = "Erro na autenticação Firebase"):
        super().__init__(message)
        self.code = "FIREBASE_AUTH_ERROR"


# === Exceções de Autorização ===

class AuthorizationError(CRMException):
    """Erro de autorização/permissão."""
    
    def __init__(self, message: str = "Acesso negado"):
        super().__init__(message, code="AUTHORIZATION_ERROR")


class InsufficientPermissionsError(AuthorizationError):
    """Usuário não tem permissão para a ação."""
    
    def __init__(self, action: str):
        super().__init__(f"Permissão insuficiente para: {action}")
        self.code = "INSUFFICIENT_PERMISSIONS"


class TenantAccessError(AuthorizationError):
    """Tentativa de acesso a dados de outro tenant."""
    
    def __init__(self):
        super().__init__("Acesso não permitido a este recurso")
        self.code = "TENANT_ACCESS_DENIED"


# === Exceções de Recursos ===

class ResourceNotFoundError(CRMException):
    """Recurso não encontrado."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: UUID | str | None = None,
    ):
        message = f"{resource_type} não encontrado"
        if resource_id:
            message = f"{resource_type} com ID {resource_id} não encontrado"
        super().__init__(message, code="NOT_FOUND")
        self.resource_type = resource_type
        self.resource_id = resource_id


class ResourceAlreadyExistsError(CRMException):
    """Recurso já existe (conflito)."""
    
    def __init__(
        self,
        resource_type: str,
        field: str,
        value: str,
    ):
        message = f"{resource_type} com {field}='{value}' já existe"
        super().__init__(message, code="ALREADY_EXISTS")
        self.resource_type = resource_type
        self.field = field
        self.value = value


# === Exceções de Validação ===

class ValidationError(CRMException):
    """Erro de validação de dados."""
    
    def __init__(
        self,
        message: str,
        field: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ):
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field
        self.errors = errors or []


class InvalidCPFError(ValidationError):
    """CPF inválido."""
    
    def __init__(self, cpf: str):
        super().__init__(f"CPF inválido: {cpf}", field="cpf")
        self.code = "INVALID_CPF"


class InvalidCNPJError(ValidationError):
    """CNPJ inválido."""
    
    def __init__(self, cnpj: str):
        super().__init__(f"CNPJ inválido: {cnpj}", field="cnpj")
        self.code = "INVALID_CNPJ"


class InvalidCNJError(ValidationError):
    """Número CNJ inválido."""
    
    def __init__(self, numero_cnj: str):
        super().__init__(f"Número CNJ inválido: {numero_cnj}", field="numero_cnj")
        self.code = "INVALID_CNJ"


# === Exceções de Negócio ===

class BusinessRuleError(CRMException):
    """Violação de regra de negócio."""
    
    def __init__(self, message: str, rule: str | None = None):
        super().__init__(message, code="BUSINESS_RULE_VIOLATION")
        self.rule = rule


class LGPDConsentRequiredError(BusinessRuleError):
    """Consentimento LGPD obrigatório."""
    
    def __init__(self):
        super().__init__(
            "Consentimento LGPD é obrigatório para cadastro de cliente",
            rule="LGPD_CONSENT_REQUIRED",
        )
        self.code = "LGPD_CONSENT_REQUIRED"


class PrazoVencidoError(BusinessRuleError):
    """Prazo já vencido."""
    
    def __init__(self, prazo_id: UUID, data_fatal: str):
        super().__init__(
            f"Prazo {prazo_id} vencido em {data_fatal}",
            rule="PRAZO_VENCIDO",
        )
        self.code = "PRAZO_VENCIDO"


class ProcessoArquivadoError(BusinessRuleError):
    """Processo arquivado não pode ser modificado."""
    
    def __init__(self, processo_id: UUID):
        super().__init__(
            f"Processo {processo_id} está arquivado e não pode ser modificado",
            rule="PROCESSO_ARQUIVADO",
        )
        self.code = "PROCESSO_ARQUIVADO"


# === Exceções de Storage/Documentos ===

class StorageError(CRMException):
    """Erro de armazenamento (GCS)."""
    
    def __init__(self, message: str, operation: str | None = None):
        super().__init__(message, code="STORAGE_ERROR")
        self.operation = operation


class FileUploadError(StorageError):
    """Erro no upload de arquivo."""
    
    def __init__(self, message: str = "Erro no upload do arquivo"):
        super().__init__(message, operation="upload")
        self.code = "FILE_UPLOAD_ERROR"


class FileTooLargeError(StorageError):
    """Arquivo muito grande."""
    
    def __init__(self, max_size_mb: int, actual_size_mb: float):
        super().__init__(
            f"Arquivo muito grande. Máximo: {max_size_mb}MB, enviado: {actual_size_mb:.2f}MB",
            operation="upload",
        )
        self.code = "FILE_TOO_LARGE"


class InvalidFileTypeError(StorageError):
    """Tipo de arquivo não permitido."""
    
    def __init__(self, mime_type: str, allowed_types: list[str]):
        super().__init__(
            f"Tipo de arquivo não permitido: {mime_type}. Permitidos: {', '.join(allowed_types)}",
            operation="upload",
        )
        self.code = "INVALID_FILE_TYPE"


# === Exceções de IA ===

class AIServiceError(CRMException):
    """Erro no serviço de IA."""
    
    def __init__(self, message: str, service: str = "gemini"):
        super().__init__(message, code="AI_SERVICE_ERROR")
        self.service = service


class DocumentExtractionError(AIServiceError):
    """Erro na extração de dados do documento."""
    
    def __init__(self, document_type: str):
        super().__init__(f"Erro ao extrair dados do documento: {document_type}")
        self.code = "DOCUMENT_EXTRACTION_ERROR"


# === Exceções de Integração ===

class ExternalServiceError(CRMException):
    """Erro em serviço externo."""
    
    def __init__(self, service: str, message: str):
        super().__init__(f"Erro no serviço {service}: {message}", code="EXTERNAL_SERVICE_ERROR")
        self.service = service
