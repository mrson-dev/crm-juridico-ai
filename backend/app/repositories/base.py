"""
Repository base com operações CRUD genéricas.
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base, MultiTenantBase

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Repository base com operações CRUD.
    
    Uso:
        class ClienteRepository(BaseRepository[Cliente]):
            def __init__(self, db: AsyncSession):
                super().__init__(Cliente, db)
    """
    
    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def get_by_id(self, id: UUID) -> ModelType | None:
        """Busca entidade por ID."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Lista todas as entidades com paginação."""
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def count(self) -> int:
        """Conta total de entidades."""
        result = await self.db.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()
    
    async def create(self, **kwargs: Any) -> ModelType:
        """Cria nova entidade."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance
    
    async def update(
        self,
        id: UUID,
        **kwargs: Any,
    ) -> ModelType | None:
        """Atualiza entidade existente."""
        instance = await self.get_by_id(id)
        if not instance:
            return None
        
        for key, value in kwargs.items():
            if value is not None:
                setattr(instance, key, value)
        
        await self.db.commit()
        await self.db.refresh(instance)
        return instance
    
    async def delete(self, id: UUID) -> bool:
        """Remove entidade (hard delete)."""
        instance = await self.get_by_id(id)
        if not instance:
            return False
        
        await self.db.delete(instance)
        await self.db.commit()
        return True
    
    async def soft_delete(self, id: UUID) -> ModelType | None:
        """Desativa entidade (soft delete)."""
        return await self.update(id, is_active=False)


class MultiTenantRepository(BaseRepository[ModelType]):
    """
    Repository com suporte a multi-tenancy.
    
    Todas as queries são automaticamente filtradas por escritorio_id.
    """
    
    def __init__(
        self,
        model: type[ModelType],
        db: AsyncSession,
        escritorio_id: UUID,
    ):
        super().__init__(model, db)
        self.escritorio_id = escritorio_id
    
    async def get_by_id(self, id: UUID) -> ModelType | None:
        """Busca entidade por ID com filtro de tenant."""
        if not issubclass(self.model, MultiTenantBase):
            return await super().get_by_id(id)
        
        result = await self.db.execute(
            select(self.model).where(
                self.model.id == id,
                self.model.escritorio_id == self.escritorio_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Lista entidades do tenant com paginação."""
        if not issubclass(self.model, MultiTenantBase):
            return await super().get_all(skip, limit)
        
        result = await self.db.execute(
            select(self.model)
            .where(self.model.escritorio_id == self.escritorio_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count(self) -> int:
        """Conta entidades do tenant."""
        if not issubclass(self.model, MultiTenantBase):
            return await super().count()
        
        result = await self.db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.escritorio_id == self.escritorio_id)
        )
        return result.scalar_one()
    
    async def create(self, **kwargs: Any) -> ModelType:
        """Cria entidade vinculada ao tenant."""
        if issubclass(self.model, MultiTenantBase):
            kwargs["escritorio_id"] = self.escritorio_id
        return await super().create(**kwargs)
