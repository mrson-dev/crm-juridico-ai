"""
Service de Escritório.

Gerencia configurações e dados do escritório (tenant).
"""

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleError,
    ResourceNotFoundError,
)
from app.models.escritorio import Escritorio
from app.repositories.escritorio_repository import EscritorioRepository
from app.schemas.escritorio import (
    EscritorioCreate,
    EscritorioUpdate,
)

logger = structlog.get_logger()


class EscritorioService:
    """
    Service para gestão de escritórios (tenants).
    
    Gerencia cadastro e configurações dos escritórios de advocacia.
    """
    
    def __init__(self, db: AsyncSession):
        self._db = db
        self._repo = EscritorioRepository(db)
    
    async def criar_escritorio(self, dados: EscritorioCreate) -> Escritorio:
        """
        Cria novo escritório.
        
        Valida CNPJ e email únicos.
        """
        # Verifica CNPJ único
        if dados.cnpj:
            existente = await self._repo.get_by_cnpj(dados.cnpj)
            if existente:
                raise BusinessRuleError(f"CNPJ {dados.cnpj} já cadastrado")
        
        # Verifica email único
        existente = await self._repo.get_by_email(dados.email)
        if existente:
            raise BusinessRuleError(f"Email {dados.email} já cadastrado")
        
        escritorio = await self._repo.create(**dados.model_dump())
        
        logger.info(
            "Escritório criado",
            escritorio_id=str(escritorio.id),
            nome=escritorio.nome_fantasia,
        )
        
        return escritorio
    
    async def buscar_escritorio(self, escritorio_id: UUID) -> Escritorio:
        """Busca escritório por ID."""
        escritorio = await self._repo.get_by_id(escritorio_id)
        if not escritorio:
            raise ResourceNotFoundError("Escritório", escritorio_id)
        return escritorio
    
    async def buscar_por_cnpj(self, cnpj: str) -> Escritorio | None:
        """Busca escritório por CNPJ."""
        return await self._repo.get_by_cnpj(cnpj)
    
    async def listar_escritorios(
        self,
        skip: int = 0,
        limit: int = 20,
        apenas_ativos: bool = True,
    ) -> list[Escritorio]:
        """Lista escritórios."""
        if apenas_ativos:
            return await self._repo.get_ativos()
        return await self._repo.get_all(skip, limit)
    
    async def atualizar_escritorio(
        self,
        escritorio_id: UUID,
        dados: EscritorioUpdate,
    ) -> Escritorio:
        """Atualiza dados do escritório."""
        escritorio = await self.buscar_escritorio(escritorio_id)
        
        # Valida CNPJ se alterado
        if dados.cnpj and dados.cnpj != escritorio.cnpj:
            existente = await self._repo.get_by_cnpj(dados.cnpj)
            if existente and existente.id != escritorio_id:
                raise BusinessRuleError(f"CNPJ {dados.cnpj} já cadastrado")
        
        # Valida email se alterado
        if dados.email and dados.email != escritorio.email:
            existente = await self._repo.get_by_email(dados.email)
            if existente and existente.id != escritorio_id:
                raise BusinessRuleError(f"Email {dados.email} já cadastrado")
        
        escritorio = await self._repo.update(
            escritorio_id,
            **dados.model_dump(exclude_unset=True),
        )
        
        logger.info(
            "Escritório atualizado",
            escritorio_id=str(escritorio_id),
        )
        
        return escritorio
    
    async def desativar_escritorio(self, escritorio_id: UUID) -> Escritorio:
        """Desativa escritório (soft delete)."""
        escritorio = await self.buscar_escritorio(escritorio_id)
        
        escritorio = await self._repo.soft_delete(escritorio_id)
        
        logger.info(
            "Escritório desativado",
            escritorio_id=str(escritorio_id),
        )
        
        return escritorio
    
    async def reativar_escritorio(self, escritorio_id: UUID) -> Escritorio:
        """Reativa escritório desativado."""
        escritorio = await self._repo.get_by_id(escritorio_id)
        if not escritorio:
            raise ResourceNotFoundError("Escritório", escritorio_id)
        
        escritorio = await self._repo.update(escritorio_id, is_active=True)
        
        logger.info(
            "Escritório reativado",
            escritorio_id=str(escritorio_id),
        )
        
        return escritorio
    
    async def atualizar_configuracoes(
        self,
        escritorio_id: UUID,
        configuracoes: dict,
    ) -> Escritorio:
        """
        Atualiza configurações personalizadas do escritório.
        
        Configurações disponíveis:
        - dias_alerta_prazo: dias antes do prazo para alertar
        - tipos_beneficio_ativos: lista de tipos de benefício utilizados
        - modelo_peticao_padrao: modelo padrão para petições
        """
        escritorio = await self.buscar_escritorio(escritorio_id)
        
        # Merge com configurações existentes
        config_atual = escritorio.configuracoes or {}
        config_atual.update(configuracoes)
        
        escritorio = await self._repo.update(
            escritorio_id,
            configuracoes=config_atual,
        )
        
        logger.info(
            "Configurações do escritório atualizadas",
            escritorio_id=str(escritorio_id),
            chaves=list(configuracoes.keys()),
        )
        
        return escritorio
