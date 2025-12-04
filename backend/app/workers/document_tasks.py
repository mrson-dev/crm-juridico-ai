"""
Tasks de processamento de documentos.

Tarefas assíncronas para OCR, extração IA e processamento de PDFs.
"""

import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings

logger = structlog.get_logger()


async def get_async_session() -> AsyncSession:
    """Cria sessão async para uso nas tasks."""
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def processar_documento_task(self, documento_id: str, escritorio_id: str):
    """
    Processa documento com IA.
    
    Chamado após upload para extração automática de dados.
    """
    import asyncio
    from uuid import UUID
    
    async def _process():
        from app.services.documento_service import DocumentoService
        
        session = await get_async_session()
        try:
            service = DocumentoService(session, UUID(escritorio_id))
            documento = await service.processar_com_ia(UUID(documento_id))
            
            logger.info(
                "Documento processado com sucesso",
                documento_id=documento_id,
                task_id=self.request.id,
            )
            
            return {"status": "success", "documento_id": documento_id}
            
        except Exception as e:
            logger.error(
                "Erro ao processar documento",
                documento_id=documento_id,
                error=str(e),
            )
            raise self.retry(exc=e)
        finally:
            await session.close()
    
    return asyncio.run(_process())


@shared_task(bind=True)
def processar_documentos_pendentes_task(self):
    """
    Processa documentos aguardando na fila de IA.
    
    Executado periodicamente pelo beat schedule.
    """
    import asyncio
    from uuid import UUID
    
    from app.repositories.documento_repository import DocumentoRepository
    
    async def _process_pending():
        session = await get_async_session()
        processed = 0
        
        try:
            # Busca escritórios com documentos pendentes
            # Simplificação: processa de todos os escritórios
            # Em produção, seria melhor ter uma fila por escritório
            
            from sqlalchemy import select
            from app.models.documento import Documento, StatusProcessamentoIA
            from app.services.documento_service import DocumentoService
            
            result = await session.execute(
                select(Documento)
                .where(Documento.status_ia == StatusProcessamentoIA.PENDENTE)
                .where(Documento.is_active == True)
                .limit(10)  # Processa até 10 por vez
            )
            documentos = result.scalars().all()
            
            for doc in documentos:
                try:
                    service = DocumentoService(session, doc.escritorio_id)
                    await service.processar_com_ia(doc.id)
                    processed += 1
                except Exception as e:
                    logger.error(
                        "Erro ao processar documento pendente",
                        documento_id=str(doc.id),
                        error=str(e),
                    )
            
            logger.info(
                "Documentos pendentes processados",
                total_processados=processed,
            )
            
            return {"processed": processed}
            
        finally:
            await session.close()
    
    return asyncio.run(_process_pending())


@shared_task(bind=True, max_retries=2)
def extrair_cnis_task(self, documento_id: str, escritorio_id: str, cliente_id: str):
    """
    Extrai dados do CNIS e atualiza histórico do cliente.
    
    Processamento especializado para documentos previdenciários.
    """
    import asyncio
    from uuid import UUID
    
    async def _extract():
        from app.services.documento_service import DocumentoService
        from app.ai.gemini_service import GeminiService
        
        session = await get_async_session()
        try:
            doc_service = DocumentoService(session, UUID(escritorio_id))
            documento = await doc_service.buscar_documento(UUID(documento_id))
            
            # Download do arquivo
            from app.core.storage import StorageService
            storage = StorageService()
            file_content = await storage.download_file(documento.storage_path)
            
            # Extração via Gemini
            gemini = GeminiService()
            dados_cnis = await gemini.extract_cnis(file_content, documento.mime_type)
            
            # Atualiza documento com dados extraídos
            from app.models.documento import StatusProcessamentoIA
            await doc_service._repo.update(
                UUID(documento_id),
                status_ia=StatusProcessamentoIA.CONCLUIDO,
                dados_extraidos=dados_cnis,
            )
            
            # TODO: Criar registros de vínculos/contribuições no histórico do cliente
            
            logger.info(
                "CNIS extraído com sucesso",
                documento_id=documento_id,
                vinculos=len(dados_cnis.get("vinculos", [])),
            )
            
            return {"status": "success", "dados": dados_cnis}
            
        except Exception as e:
            logger.error(
                "Erro ao extrair CNIS",
                documento_id=documento_id,
                error=str(e),
            )
            raise self.retry(exc=e)
        finally:
            await session.close()
    
    return asyncio.run(_extract())


@shared_task(bind=True, max_retries=2)
def analisar_ppp_task(self, documento_id: str, escritorio_id: str, processo_id: str):
    """
    Analisa PPP para identificar tempo especial.
    
    Importante para aposentadoria especial (25/20/15 anos).
    """
    import asyncio
    from uuid import UUID
    
    async def _analyze():
        from app.services.documento_service import DocumentoService
        from app.ai.gemini_service import GeminiService
        
        session = await get_async_session()
        try:
            doc_service = DocumentoService(session, UUID(escritorio_id))
            documento = await doc_service.buscar_documento(UUID(documento_id))
            
            # Download
            from app.core.storage import StorageService
            storage = StorageService()
            file_content = await storage.download_file(documento.storage_path)
            
            # Análise via Gemini
            gemini = GeminiService()
            analise_ppp = await gemini.analyze_ppp(file_content, documento.mime_type)
            
            # Atualiza documento
            from app.models.documento import StatusProcessamentoIA
            await doc_service._repo.update(
                UUID(documento_id),
                status_ia=StatusProcessamentoIA.CONCLUIDO,
                dados_extraidos=analise_ppp,
            )
            
            # Se identificou exposição a agentes nocivos, pode criar alerta
            if analise_ppp.get("agentes_nocivos"):
                logger.info(
                    "PPP com agentes nocivos identificados",
                    documento_id=documento_id,
                    agentes=analise_ppp["agentes_nocivos"],
                )
            
            return {"status": "success", "analise": analise_ppp}
            
        except Exception as e:
            logger.error(
                "Erro ao analisar PPP",
                documento_id=documento_id,
                error=str(e),
            )
            raise self.retry(exc=e)
        finally:
            await session.close()
    
    return asyncio.run(_analyze())


@shared_task
def limpar_documentos_excluidos_task():
    """
    Remove arquivos físicos de documentos marcados como excluídos.
    
    Job de manutenção executado semanalmente.
    """
    import asyncio
    from datetime import datetime, timedelta, timezone
    
    async def _cleanup():
        from sqlalchemy import select, and_
        from app.models.documento import Documento
        from app.core.storage import StorageService
        
        session = await get_async_session()
        storage = StorageService()
        deleted = 0
        
        try:
            # Documentos excluídos há mais de 30 dias
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            
            result = await session.execute(
                select(Documento)
                .where(
                    and_(
                        Documento.is_active == False,
                        Documento.updated_at < cutoff,
                    )
                )
                .limit(100)
            )
            documentos = result.scalars().all()
            
            for doc in documentos:
                try:
                    # Remove do GCS
                    await storage.delete_file(doc.storage_path)
                    
                    # Remove do banco (hard delete)
                    await session.delete(doc)
                    deleted += 1
                    
                except Exception as e:
                    logger.warning(
                        "Erro ao limpar documento",
                        documento_id=str(doc.id),
                        error=str(e),
                    )
            
            await session.commit()
            
            logger.info(
                "Limpeza de documentos concluída",
                documentos_removidos=deleted,
            )
            
            return {"deleted": deleted}
            
        finally:
            await session.close()
    
    return asyncio.run(_cleanup())
