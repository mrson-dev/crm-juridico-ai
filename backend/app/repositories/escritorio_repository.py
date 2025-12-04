"""
Repository do Escritório.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.escritorio import Escritorio
from app.repositories.base import BaseRepository


class EscritorioRepository(BaseRepository[Escritorio]):
    """Repository para operações com Escritório."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Escritorio, db)
    
    async def get_by_cnpj(self, cnpj: str) -> Escritorio | None:
        """Busca escritório por CNPJ."""
        result = await self.db.execute(
            select(Escritorio).where(Escritorio.cnpj == cnpj)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Escritorio | None:
        """Busca escritório por email."""
        result = await self.db.execute(
            select(Escritorio).where(Escritorio.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_ativos(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Escritorio]:
        """Lista escritórios ativos."""
        result = await self.db.execute(
            select(Escritorio)
            .where(Escritorio.is_active == True)  # noqa: E712
            .order_by(Escritorio.nome)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
