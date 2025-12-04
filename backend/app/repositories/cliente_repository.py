"""
Repository do Cliente.
"""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.repositories.base import MultiTenantRepository


class ClienteRepository(MultiTenantRepository[Cliente]):
    """Repository para operações com Cliente."""
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        super().__init__(Cliente, db, escritorio_id)
    
    async def get_by_cpf(self, cpf: str) -> Cliente | None:
        """Busca cliente por CPF no tenant."""
        result = await self.db.execute(
            select(Cliente).where(
                Cliente.cpf == cpf,
                Cliente.escritorio_id == self.escritorio_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Cliente]:
        """Busca clientes por nome, CPF ou email."""
        search_term = f"%{query}%"
        result = await self.db.execute(
            select(Cliente)
            .where(
                Cliente.escritorio_id == self.escritorio_id,
                or_(
                    Cliente.nome.ilike(search_term),
                    Cliente.cpf.ilike(search_term),
                    Cliente.email.ilike(search_term),
                ),
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_ativos(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Cliente]:
        """Lista apenas clientes ativos."""
        result = await self.db.execute(
            select(Cliente)
            .where(
                Cliente.escritorio_id == self.escritorio_id,
                Cliente.is_active == True,  # noqa: E712
            )
            .order_by(Cliente.nome)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
