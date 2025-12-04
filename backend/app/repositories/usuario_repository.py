"""
Repository do Usuário.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario, UserRole
from app.repositories.base import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    """Repository para operações com Usuário."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Usuario, db)
    
    async def get_by_email(self, email: str) -> Usuario | None:
        """Busca usuário por email."""
        result = await self.db.execute(
            select(Usuario).where(Usuario.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_firebase_uid(self, firebase_uid: str) -> Usuario | None:
        """Busca usuário pelo UID do Firebase."""
        result = await self.db.execute(
            select(Usuario).where(Usuario.firebase_uid == firebase_uid)
        )
        return result.scalar_one_or_none()
    
    async def get_by_escritorio(
        self,
        escritorio_id: UUID,
        skip: int = 0,
        limit: int = 100,
        apenas_ativos: bool = True,
    ) -> list[Usuario]:
        """Lista usuários de um escritório."""
        query = select(Usuario).where(Usuario.escritorio_id == escritorio_id)
        
        if apenas_ativos:
            query = query.where(Usuario.is_active == True)  # noqa: E712
        
        result = await self.db.execute(
            query.order_by(Usuario.nome).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_advogados_by_escritorio(
        self,
        escritorio_id: UUID,
    ) -> list[Usuario]:
        """Lista advogados de um escritório."""
        result = await self.db.execute(
            select(Usuario).where(
                Usuario.escritorio_id == escritorio_id,
                Usuario.role.in_([UserRole.ADMIN, UserRole.ADVOGADO]),
                Usuario.is_active == True,  # noqa: E712
            ).order_by(Usuario.nome)
        )
        return list(result.scalars().all())
    
    async def count_by_escritorio(self, escritorio_id: UUID) -> int:
        """Conta usuários de um escritório."""
        from sqlalchemy import func
        
        result = await self.db.execute(
            select(func.count())
            .select_from(Usuario)
            .where(Usuario.escritorio_id == escritorio_id)
        )
        return result.scalar_one()
