"""
Repository de Processo, Prazo e Andamento.
"""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.processo import (
    Andamento,
    FaseProcessual,
    Prazo,
    Processo,
    StatusPrazo,
)
from app.repositories.base import MultiTenantRepository


class ProcessoRepository(MultiTenantRepository[Processo]):
    """Repository para operações com Processo."""
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        super().__init__(Processo, db, escritorio_id)
    
    async def get_by_id_with_relations(self, id: UUID) -> Processo | None:
        """Busca processo com todas as relações carregadas."""
        result = await self.db.execute(
            select(Processo)
            .where(
                Processo.id == id,
                Processo.escritorio_id == self.escritorio_id,
            )
            .options(
                selectinload(Processo.prazos),
                selectinload(Processo.andamentos),
                selectinload(Processo.documentos),
                selectinload(Processo.cliente),
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_numero_cnj(self, numero_cnj: str) -> Processo | None:
        """Busca processo por número CNJ."""
        result = await self.db.execute(
            select(Processo).where(
                Processo.numero_cnj == numero_cnj,
                Processo.escritorio_id == self.escritorio_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_cliente(
        self,
        cliente_id: UUID,
        include_archived: bool = False,
    ) -> list[Processo]:
        """Lista processos de um cliente."""
        query = select(Processo).where(
            Processo.cliente_id == cliente_id,
            Processo.escritorio_id == self.escritorio_id,
        )
        
        if not include_archived:
            query = query.where(Processo.is_archived == False)  # noqa: E712
        
        result = await self.db.execute(query.order_by(Processo.data_entrada.desc()))
        return list(result.scalars().all())
    
    async def get_by_fase(self, fase: FaseProcessual) -> list[Processo]:
        """Lista processos em determinada fase."""
        result = await self.db.execute(
            select(Processo)
            .where(
                Processo.fase == fase,
                Processo.escritorio_id == self.escritorio_id,
                Processo.is_archived == False,  # noqa: E712
            )
            .order_by(Processo.data_entrada.desc())
        )
        return list(result.scalars().all())
    
    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Processo]:
        """Busca processos por número ou objeto."""
        search_term = f"%{query}%"
        result = await self.db.execute(
            select(Processo)
            .where(
                Processo.escritorio_id == self.escritorio_id,
                or_(
                    Processo.numero_cnj.ilike(search_term),
                    Processo.numero_administrativo.ilike(search_term),
                    Processo.objeto.ilike(search_term),
                ),
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_stats(self) -> dict:
        """Retorna estatísticas dos processos do escritório."""
        # Total
        total = await self.count()
        
        # Por fase
        fase_result = await self.db.execute(
            select(Processo.fase, func.count())
            .where(
                Processo.escritorio_id == self.escritorio_id,
                Processo.is_archived == False,  # noqa: E712
            )
            .group_by(Processo.fase)
        )
        por_fase = {str(row[0].value): row[1] for row in fase_result.all()}
        
        # Por tipo de benefício
        tipo_result = await self.db.execute(
            select(Processo.tipo_beneficio, func.count())
            .where(
                Processo.escritorio_id == self.escritorio_id,
                Processo.is_archived == False,  # noqa: E712
            )
            .group_by(Processo.tipo_beneficio)
        )
        por_tipo = {str(row[0].value): row[1] for row in tipo_result.all()}
        
        return {
            "total": total,
            "por_fase": por_fase,
            "por_tipo_beneficio": por_tipo,
        }


class PrazoRepository(MultiTenantRepository[Prazo]):
    """Repository para operações com Prazo."""
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        super().__init__(Prazo, db, escritorio_id)
    
    async def get_pendentes(
        self,
        dias_futuros: int = 30,
    ) -> list[Prazo]:
        """Lista prazos pendentes nos próximos X dias."""
        data_limite = date.today() + timedelta(days=dias_futuros)
        
        result = await self.db.execute(
            select(Prazo)
            .where(
                Prazo.escritorio_id == self.escritorio_id,
                Prazo.status == StatusPrazo.PENDENTE,
                Prazo.data_fatal <= data_limite,
            )
            .order_by(Prazo.data_fatal)
        )
        return list(result.scalars().all())
    
    async def get_urgentes(self, dias: int = 3) -> list[Prazo]:
        """Lista prazos que vencem em até X dias."""
        data_limite = date.today() + timedelta(days=dias)
        
        result = await self.db.execute(
            select(Prazo)
            .where(
                Prazo.escritorio_id == self.escritorio_id,
                Prazo.status == StatusPrazo.PENDENTE,
                Prazo.data_fatal <= data_limite,
                Prazo.data_fatal >= date.today(),
            )
            .order_by(Prazo.data_fatal)
        )
        return list(result.scalars().all())
    
    async def get_vencidos(self) -> list[Prazo]:
        """Lista prazos vencidos não cumpridos."""
        result = await self.db.execute(
            select(Prazo)
            .where(
                Prazo.escritorio_id == self.escritorio_id,
                Prazo.status == StatusPrazo.PENDENTE,
                Prazo.data_fatal < date.today(),
            )
            .order_by(Prazo.data_fatal)
        )
        return list(result.scalars().all())
    
    async def get_by_processo(self, processo_id: UUID) -> list[Prazo]:
        """Lista prazos de um processo."""
        result = await self.db.execute(
            select(Prazo)
            .where(
                Prazo.processo_id == processo_id,
                Prazo.escritorio_id == self.escritorio_id,
            )
            .order_by(Prazo.data_fatal)
        )
        return list(result.scalars().all())
    
    async def count_pendentes(self) -> int:
        """Conta prazos pendentes."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Prazo)
            .where(
                Prazo.escritorio_id == self.escritorio_id,
                Prazo.status == StatusPrazo.PENDENTE,
            )
        )
        return result.scalar_one()
    
    async def count_urgentes(self, dias: int = 3) -> int:
        """Conta prazos urgentes."""
        data_limite = date.today() + timedelta(days=dias)
        
        result = await self.db.execute(
            select(func.count())
            .select_from(Prazo)
            .where(
                Prazo.escritorio_id == self.escritorio_id,
                Prazo.status == StatusPrazo.PENDENTE,
                Prazo.data_fatal <= data_limite,
                Prazo.data_fatal >= date.today(),
            )
        )
        return result.scalar_one()


class AndamentoRepository(MultiTenantRepository[Andamento]):
    """Repository para operações com Andamento."""
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        super().__init__(Andamento, db, escritorio_id)
    
    async def get_by_processo(
        self,
        processo_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Andamento]:
        """Lista andamentos de um processo."""
        result = await self.db.execute(
            select(Andamento)
            .where(
                Andamento.processo_id == processo_id,
                Andamento.escritorio_id == self.escritorio_id,
            )
            .order_by(Andamento.data.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_recentes(self, dias: int = 7) -> list[Andamento]:
        """Lista andamentos recentes do escritório."""
        from datetime import datetime, timezone
        
        data_inicio = datetime.now(timezone.utc) - timedelta(days=dias)
        
        result = await self.db.execute(
            select(Andamento)
            .where(
                Andamento.escritorio_id == self.escritorio_id,
                Andamento.data >= data_inicio,
            )
            .order_by(Andamento.data.desc())
            .limit(100)
        )
        return list(result.scalars().all())
