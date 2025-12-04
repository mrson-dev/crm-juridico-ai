"""
Serviço de armazenamento no Google Cloud Storage.

Gerencia upload, download e URLs assinadas de documentos.
"""

import hashlib
import uuid
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO

import structlog
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

from app.core.config import settings
from app.core.exceptions import (
    FileTooLargeError,
    FileUploadError,
    InvalidFileTypeError,
    StorageError,
)

logger = structlog.get_logger()


class StorageService:
    """
    Serviço de armazenamento no Google Cloud Storage.
    
    Uso:
        service = StorageService()
        result = await service.upload_file(file, "documentos/cliente_123/")
    """
    
    def __init__(self):
        self._client: storage.Client | None = None
        self._bucket: storage.Bucket | None = None
    
    @property
    def client(self) -> storage.Client:
        """Inicializa cliente GCS sob demanda."""
        if self._client is None:
            self._client = storage.Client(project=settings.GCP_PROJECT_ID)
        return self._client
    
    @property
    def bucket(self) -> storage.Bucket:
        """Retorna bucket de documentos."""
        if self._bucket is None:
            self._bucket = self.client.bucket(settings.GCS_BUCKET_DOCUMENTOS)
        return self._bucket
    
    def _validate_file(
        self,
        file_size: int,
        mime_type: str,
    ) -> None:
        """Valida arquivo antes do upload."""
        # Valida tamanho
        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise FileTooLargeError(
                max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
                actual_size_mb=file_size / (1024 * 1024),
            )
        
        # Valida tipo
        if mime_type not in settings.ALLOWED_DOCUMENT_TYPES:
            raise InvalidFileTypeError(
                mime_type=mime_type,
                allowed_types=settings.ALLOWED_DOCUMENT_TYPES,
            )
    
    def _calculate_hash(self, content: bytes) -> str:
        """Calcula SHA-256 do conteúdo."""
        return hashlib.sha256(content).hexdigest()
    
    def _generate_path(
        self,
        escritorio_id: uuid.UUID,
        prefix: str,
        original_filename: str,
    ) -> str:
        """
        Gera path único no GCS.
        
        Formato: {escritorio_id}/{prefix}/{uuid}_{filename}
        """
        file_uuid = str(uuid.uuid4())[:8]
        safe_filename = Path(original_filename).name  # Remove path traversal
        return f"{escritorio_id}/{prefix}/{file_uuid}_{safe_filename}"
    
    async def upload_file(
        self,
        file_content: bytes | BinaryIO,
        original_filename: str,
        mime_type: str,
        escritorio_id: uuid.UUID,
        prefix: str = "documentos",
    ) -> dict:
        """
        Faz upload de arquivo para o GCS.
        
        Args:
            file_content: Conteúdo do arquivo (bytes ou file-like)
            original_filename: Nome original do arquivo
            mime_type: Tipo MIME
            escritorio_id: ID do escritório (tenant)
            prefix: Prefixo do path (ex: 'documentos', 'avatars')
        
        Returns:
            Dict com gcs_bucket, gcs_path, hash_sha256, tamanho_bytes
        """
        # Lê conteúdo se for file-like
        if hasattr(file_content, "read"):
            content = file_content.read()
        else:
            content = file_content
        
        # Valida
        self._validate_file(len(content), mime_type)
        
        # Gera path e hash
        gcs_path = self._generate_path(escritorio_id, prefix, original_filename)
        file_hash = self._calculate_hash(content)
        
        try:
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_string(content, content_type=mime_type)
            
            logger.info(
                "Arquivo enviado para GCS",
                gcs_path=gcs_path,
                size_bytes=len(content),
                mime_type=mime_type,
            )
            
            return {
                "gcs_bucket": settings.GCS_BUCKET_DOCUMENTOS,
                "gcs_path": gcs_path,
                "hash_sha256": file_hash,
                "tamanho_bytes": len(content),
            }
            
        except GoogleCloudError as e:
            logger.error("Erro no upload para GCS", error=str(e), gcs_path=gcs_path)
            raise FileUploadError(f"Erro ao enviar arquivo: {str(e)}")
    
    async def download_file(self, gcs_path: str) -> bytes:
        """Baixa arquivo do GCS."""
        try:
            blob = self.bucket.blob(gcs_path)
            return blob.download_as_bytes()
        except GoogleCloudError as e:
            logger.error("Erro no download do GCS", error=str(e), gcs_path=gcs_path)
            raise StorageError(f"Erro ao baixar arquivo: {str(e)}", operation="download")
    
    def generate_signed_url(
        self,
        gcs_path: str,
        expiration_minutes: int = 60,
        method: str = "GET",
    ) -> str:
        """
        Gera URL assinada para acesso temporário.
        
        Args:
            gcs_path: Caminho do arquivo no GCS
            expiration_minutes: Tempo de expiração em minutos
            method: Método HTTP permitido (GET para download, PUT para upload)
        
        Returns:
            URL assinada
        """
        try:
            blob = self.bucket.blob(gcs_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method=method,
            )
            return url
        except GoogleCloudError as e:
            logger.error("Erro ao gerar URL assinada", error=str(e), gcs_path=gcs_path)
            raise StorageError(f"Erro ao gerar URL: {str(e)}", operation="signed_url")
    
    async def delete_file(self, gcs_path: str) -> bool:
        """Remove arquivo do GCS."""
        try:
            blob = self.bucket.blob(gcs_path)
            blob.delete()
            logger.info("Arquivo removido do GCS", gcs_path=gcs_path)
            return True
        except GoogleCloudError as e:
            logger.error("Erro ao remover do GCS", error=str(e), gcs_path=gcs_path)
            raise StorageError(f"Erro ao remover arquivo: {str(e)}", operation="delete")
    
    async def copy_file(
        self,
        source_path: str,
        destination_path: str,
    ) -> str:
        """Copia arquivo dentro do bucket."""
        try:
            source_blob = self.bucket.blob(source_path)
            destination_blob = self.bucket.blob(destination_path)
            
            self.bucket.copy_blob(source_blob, self.bucket, destination_blob.name)
            
            logger.info(
                "Arquivo copiado no GCS",
                source=source_path,
                destination=destination_path,
            )
            return destination_path
        except GoogleCloudError as e:
            logger.error("Erro ao copiar no GCS", error=str(e))
            raise StorageError(f"Erro ao copiar arquivo: {str(e)}", operation="copy")
    
    def file_exists(self, gcs_path: str) -> bool:
        """Verifica se arquivo existe no GCS."""
        blob = self.bucket.blob(gcs_path)
        return blob.exists()


# Singleton para uso global
storage_service = StorageService()
