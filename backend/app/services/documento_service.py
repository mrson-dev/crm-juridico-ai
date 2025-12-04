"""
Service de Documentos.

Gerencia upload, extração IA e gestão de documentos.
"""

import hashlib
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AIServiceError,
    BusinessRuleError,
    ResourceNotFoundError,
    StorageError,
)
from app.core.storage import StorageService
from app.models.documento import (
    CategoriaDocumento,
    Documento,
    StatusProcessamentoIA,
    TipoDocumento,
)
from app.repositories.documento_repository import DocumentoRepository
from app.schemas.documento import (
    DocumentoCreate,
    DocumentoStats,
    DocumentoUpdate,
)

logger = structlog.get_logger()


class DocumentoService:
    """
    Service para gestão de documentos.
    
    Responsável por upload/download, processamento IA e metadados.
    """
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        self._db = db
        self._escritorio_id = escritorio_id
        self._repo = DocumentoRepository(db, escritorio_id)
        self._storage = StorageService()
    
    async def upload_documento(
        self,
        dados: DocumentoCreate,
        file_content: bytes,
        filename: str,
        content_type: str,
        uploaded_by_id: UUID,
    ) -> Documento:
        """
        Faz upload de documento para GCS e registra no banco.
        
        Calcula hash SHA-256 para detectar duplicatas.
        """
        # Calcula hash do arquivo
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Verifica duplicata
        existente = await self._repo.get_by_hash(file_hash)
        if existente:
            logger.warning(
                "Documento duplicado detectado",
                hash=file_hash,
                documento_id=str(existente.id),
            )
            raise BusinessRuleError(
                f"Documento já existe no sistema (ID: {existente.id})"
            )
        
        # Determina categoria pelo tipo
        categoria = self._determinar_categoria(dados.tipo)
        
        # Gera path no storage
        storage_path = self._storage.generate_file_path(
            str(self._escritorio_id),
            filename,
            prefix=categoria.value,
        )
        
        # Upload para GCS
        try:
            file_size = len(file_content)
            await self._storage.upload_file(
                file_content=file_content,
                destination_path=storage_path,
                content_type=content_type,
            )
        except StorageError as e:
            logger.error(
                "Erro no upload para GCS",
                error=str(e),
                filename=filename,
            )
            raise
        
        # Cria registro no banco
        documento = await self._repo.create(
            **dados.model_dump(),
            nome_arquivo=filename,
            storage_path=storage_path,
            mime_type=content_type,
            tamanho_bytes=file_size,
            hash_sha256=file_hash,
            categoria=categoria,
            uploaded_by_id=uploaded_by_id,
        )
        
        logger.info(
            "Documento uploaded",
            documento_id=str(documento.id),
            filename=filename,
            size_bytes=file_size,
            tipo=dados.tipo.value,
        )
        
        return documento
    
    async def buscar_documento(self, documento_id: UUID) -> Documento:
        """Busca documento por ID."""
        documento = await self._repo.get_by_id(documento_id)
        if not documento:
            raise ResourceNotFoundError("Documento", documento_id)
        return documento
    
    async def listar_documentos_cliente(
        self,
        cliente_id: UUID,
        categoria: CategoriaDocumento | None = None,
    ) -> list[Documento]:
        """Lista documentos de um cliente."""
        documentos = await self._repo.get_by_cliente(cliente_id)
        
        if categoria:
            documentos = [d for d in documentos if d.categoria == categoria]
        
        return documentos
    
    async def listar_documentos_processo(
        self,
        processo_id: UUID,
        tipo: TipoDocumento | None = None,
    ) -> list[Documento]:
        """Lista documentos de um processo."""
        if tipo:
            return await self._repo.get_by_tipo(tipo, processo_id=processo_id)
        return await self._repo.get_by_processo(processo_id)
    
    async def listar_pendentes_processamento(self) -> list[Documento]:
        """Lista documentos aguardando processamento IA."""
        return await self._repo.get_pendentes_processamento()
    
    async def atualizar_documento(
        self,
        documento_id: UUID,
        dados: DocumentoUpdate,
    ) -> Documento:
        """Atualiza metadados do documento."""
        documento = await self.buscar_documento(documento_id)
        
        documento = await self._repo.update(
            documento_id,
            **dados.model_dump(exclude_unset=True),
        )
        
        return documento
    
    async def excluir_documento(self, documento_id: UUID) -> None:
        """
        Remove documento (soft delete + marca para limpeza no GCS).
        
        O arquivo físico é removido por job agendado.
        """
        documento = await self.buscar_documento(documento_id)
        
        # Soft delete no banco
        await self._repo.soft_delete(documento_id)
        
        logger.info(
            "Documento marcado para exclusão",
            documento_id=str(documento_id),
            storage_path=documento.storage_path,
        )
    
    async def gerar_url_download(
        self,
        documento_id: UUID,
        expiration_minutes: int = 30,
    ) -> str:
        """
        Gera URL assinada temporária para download.
        
        Por padrão, URL expira em 30 minutos.
        """
        documento = await self.buscar_documento(documento_id)
        
        url = await self._storage.generate_signed_url(
            documento.storage_path,
            expiration_minutes=expiration_minutes,
            method="GET",
        )
        
        logger.info(
            "URL de download gerada",
            documento_id=str(documento_id),
            expiration_minutes=expiration_minutes,
        )
        
        return url
    
    async def processar_com_ia(self, documento_id: UUID) -> Documento:
        """
        Processa documento com IA (Gemini/Document AI).
        
        Extrai dados estruturados de acordo com o tipo do documento.
        """
        # Importação tardia para evitar dependência circular
        from app.ai.gemini_service import GeminiService
        
        documento = await self.buscar_documento(documento_id)
        
        if documento.status_ia == StatusProcessamentoIA.CONCLUIDO:
            logger.info(
                "Documento já processado",
                documento_id=str(documento_id),
            )
            return documento
        
        # Atualiza status para processando
        await self._repo.atualizar_status_ia(
            documento_id,
            StatusProcessamentoIA.PROCESSANDO,
        )
        
        try:
            # Download do arquivo
            file_content = await self._storage.download_file(documento.storage_path)
            
            # Processa com Gemini
            gemini = GeminiService()
            resultado = await self._processar_por_tipo(
                gemini,
                documento.tipo,
                file_content,
                documento.mime_type,
            )
            
            # Salva resultado
            await self._repo.update(
                documento_id,
                status_ia=StatusProcessamentoIA.CONCLUIDO,
                dados_extraidos=resultado,
                processado_em=documento.updated_at,
            )
            
            logger.info(
                "Documento processado com IA",
                documento_id=str(documento_id),
                tipo=documento.tipo.value,
                campos_extraidos=list(resultado.keys()) if resultado else [],
            )
            
            documento = await self.buscar_documento(documento_id)
            return documento
            
        except AIServiceError as e:
            await self._repo.atualizar_status_ia(
                documento_id,
                StatusProcessamentoIA.ERRO,
                erro=str(e),
            )
            logger.error(
                "Falha no processamento IA",
                documento_id=str(documento_id),
                error=str(e),
            )
            raise
    
    async def get_stats(self) -> DocumentoStats:
        """Retorna estatísticas dos documentos."""
        documentos = await self._repo.get_all(limit=10000)
        
        total = len(documentos)
        por_tipo = {}
        por_status_ia = {}
        tamanho_total = 0
        
        for doc in documentos:
            # Por tipo
            tipo_key = doc.tipo.value if doc.tipo else "sem_tipo"
            por_tipo[tipo_key] = por_tipo.get(tipo_key, 0) + 1
            
            # Por status IA
            status_key = doc.status_ia.value if doc.status_ia else "sem_status"
            por_status_ia[status_key] = por_status_ia.get(status_key, 0) + 1
            
            # Tamanho
            tamanho_total += doc.tamanho_bytes or 0
        
        pendentes = await self._repo.get_pendentes_processamento()
        
        return DocumentoStats(
            total=total,
            por_tipo=por_tipo,
            por_status_ia=por_status_ia,
            tamanho_total_bytes=tamanho_total,
            pendentes_processamento=len(pendentes),
        )
    
    # === MÉTODOS AUXILIARES ===
    
    def _determinar_categoria(self, tipo: TipoDocumento) -> CategoriaDocumento:
        """Determina categoria baseado no tipo do documento."""
        categorias_map = {
            # Identificação
            TipoDocumento.RG: CategoriaDocumento.IDENTIFICACAO,
            TipoDocumento.CPF: CategoriaDocumento.IDENTIFICACAO,
            TipoDocumento.CNH: CategoriaDocumento.IDENTIFICACAO,
            TipoDocumento.CERTIDAO_NASCIMENTO: CategoriaDocumento.IDENTIFICACAO,
            TipoDocumento.CERTIDAO_CASAMENTO: CategoriaDocumento.IDENTIFICACAO,
            TipoDocumento.TITULO_ELEITOR: CategoriaDocumento.IDENTIFICACAO,
            TipoDocumento.COMPROVANTE_RESIDENCIA: CategoriaDocumento.IDENTIFICACAO,
            
            # Previdenciário
            TipoDocumento.CNIS: CategoriaDocumento.PREVIDENCIARIO,
            TipoDocumento.CTPS: CategoriaDocumento.PREVIDENCIARIO,
            TipoDocumento.PPP: CategoriaDocumento.PREVIDENCIARIO,
            TipoDocumento.CARTA_CONCESSAO: CategoriaDocumento.PREVIDENCIARIO,
            TipoDocumento.CARTA_INDEFERIMENTO: CategoriaDocumento.PREVIDENCIARIO,
            
            # Médico
            TipoDocumento.LAUDO_MEDICO: CategoriaDocumento.MEDICO,
            TipoDocumento.ATESTADO: CategoriaDocumento.MEDICO,
            TipoDocumento.EXAME: CategoriaDocumento.MEDICO,
            TipoDocumento.RECEITUARIO: CategoriaDocumento.MEDICO,
            
            # Processual
            TipoDocumento.PROCURACAO: CategoriaDocumento.PROCESSUAL,
            TipoDocumento.PETICAO_INICIAL: CategoriaDocumento.PROCESSUAL,
            TipoDocumento.CONTESTACAO: CategoriaDocumento.PROCESSUAL,
            TipoDocumento.RECURSO: CategoriaDocumento.PROCESSUAL,
            TipoDocumento.SENTENCA: CategoriaDocumento.PROCESSUAL,
            TipoDocumento.ACORDAO: CategoriaDocumento.PROCESSUAL,
            TipoDocumento.MANDADO: CategoriaDocumento.PROCESSUAL,
            
            # Financeiro
            TipoDocumento.CONTRATO_HONORARIOS: CategoriaDocumento.FINANCEIRO,
            TipoDocumento.COMPROVANTE_PAGAMENTO: CategoriaDocumento.FINANCEIRO,
        }
        
        return categorias_map.get(tipo, CategoriaDocumento.OUTROS)
    
    async def _processar_por_tipo(
        self,
        gemini,
        tipo: TipoDocumento,
        file_content: bytes,
        mime_type: str,
    ) -> dict:
        """Processa documento com método apropriado para o tipo."""
        # Documentos de identidade
        if tipo in [TipoDocumento.RG, TipoDocumento.CNH, TipoDocumento.CPF]:
            return await gemini.extract_identity_document(file_content, mime_type)
        
        # CNIS
        if tipo == TipoDocumento.CNIS:
            return await gemini.extract_cnis(file_content, mime_type)
        
        # PPP
        if tipo == TipoDocumento.PPP:
            return await gemini.analyze_ppp(file_content, mime_type)
        
        # Padrão: resumo estruturado
        return await gemini.summarize_document(file_content, mime_type)
