"""
Repository de Documentos.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documento import Documento, StatusProcessamentoIA, TipoDocumento
from app.repositories.base import MultiTenantRepository


class DocumentoRepository(MultiTenantRepository[Documento]):
    """Repository para operações com Documento."""
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        super().__init__(Documento, db, escritorio_id)
    
    async def get_by_cliente(
        self,
        cliente_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Documento]:
        """Lista documentos de um cliente."""
        result = await self.db.execute(
            select(Documento)
            .where(
                Documento.escritorio_id == self.escritorio_id,
                Documento.cliente_id == cliente_id,
            )
            .order_by(Documento.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_processo(
        self,
        processo_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Documento]:
        """Lista documentos de um processo."""
        result = await self.db.execute(
            select(Documento)
            .where(
                Documento.escritorio_id == self.escritorio_id,
                Documento.processo_id == processo_id,
            )
            .order_by(Documento.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_tipo(
        self,
        tipo: TipoDocumento,
        cliente_id: UUID | None = None,
        processo_id: UUID | None = None,
    ) -> list[Documento]:
        """Lista documentos de um tipo específico."""
        query = select(Documento).where(
            Documento.escritorio_id == self.escritorio_id,
            Documento.tipo == tipo,
        )
        
        if cliente_id:
            query = query.where(Documento.cliente_id == cliente_id)
        if processo_id:
            query = query.where(Documento.processo_id == processo_id)
        
        result = await self.db.execute(query.order_by(Documento.created_at.desc()))
        return list(result.scalars().all())
    
    async def get_pendentes_processamento(
        self,
        limit: int = 10,
    ) -> list[Documento]:
        """Lista documentos pendentes de processamento IA."""
        result = await self.db.execute(
            select(Documento)
            .where(
                Documento.escritorio_id == self.escritorio_id,
                Documento.status_ia == StatusProcessamentoIA.PENDENTE,
            )
            .order_by(Documento.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def atualizar_status_ia(
        self,
        documento_id: UUID,
        status: StatusProcessamentoIA,
        dados_extraidos: str | None = None,
        resumo_ia: str | None = None,
    ) -> None:
        """Atualiza status de processamento IA do documento."""
        update_data = {
            "status_ia": status,
        }
        
        if status == StatusProcessamentoIA.CONCLUIDO:
            update_data["processado_em"] = datetime.now(timezone.utc)
            if dados_extraidos:
                update_data["dados_extraidos"] = dados_extraidos
            if resumo_ia:
                update_data["resumo_ia"] = resumo_ia
        
        await self.db.execute(
            update(Documento)
            .where(
                Documento.id == documento_id,
                Documento.escritorio_id == self.escritorio_id,
            )
            .values(**update_data)
        )
        await self.db.commit()
    
    async def get_by_hash(self, hash_sha256: str) -> Documento | None:
        """Busca documento por hash (para evitar duplicatas)."""
        result = await self.db.execute(
            select(Documento).where(
                Documento.escritorio_id == self.escritorio_id,
                Documento.hash_sha256 == hash_sha256,
            )
        )
        return result.scalar_one_or_none()
