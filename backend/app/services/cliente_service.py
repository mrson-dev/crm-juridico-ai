"""
Service do Cliente com integração IA para extração de documentos.
"""

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.repositories.cliente_repository import ClienteRepository
from app.schemas.cliente import ClienteCreate, ClienteFromDocumentAI, ClienteUpdate


class ClienteService:
    """
    Service para operações com Cliente.
    
    Encapsula lógica de negócio e coordena repositories/services.
    """
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        self._repo = ClienteRepository(db, escritorio_id)
        self._db = db
        self._escritorio_id = escritorio_id
    
    async def criar(self, dados: ClienteCreate) -> Cliente:
        """
        Cria novo cliente.
        
        Valida CPF único e registra consentimento LGPD.
        """
        # Verifica se CPF já existe
        if dados.cpf:
            existente = await self._repo.get_by_cpf(dados.cpf)
            if existente:
                raise ValueError(f"Já existe cliente com CPF {dados.cpf}")
        
        # Cria cliente com data de consentimento
        cliente_data = dados.model_dump()
        if dados.consentimento_lgpd:
            cliente_data["data_consentimento"] = date.today()
        
        return await self._repo.create(**cliente_data)
    
    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None:
        """Busca cliente por ID."""
        return await self._repo.get_by_id(cliente_id)
    
    async def listar(
        self,
        skip: int = 0,
        limit: int = 100,
        apenas_ativos: bool = True,
    ) -> list[Cliente]:
        """Lista clientes do escritório."""
        if apenas_ativos:
            return await self._repo.get_ativos(skip, limit)
        return await self._repo.get_all(skip, limit)
    
    async def pesquisar(self, query: str) -> list[Cliente]:
        """Pesquisa clientes por nome, CPF ou email."""
        return await self._repo.search(query)
    
    async def atualizar(
        self,
        cliente_id: UUID,
        dados: ClienteUpdate,
    ) -> Cliente | None:
        """Atualiza dados do cliente."""
        update_data = dados.model_dump(exclude_unset=True)
        return await self._repo.update(cliente_id, **update_data)
    
    async def desativar(self, cliente_id: UUID) -> Cliente | None:
        """Desativa cliente (soft delete)."""
        return await self._repo.soft_delete(cliente_id)
    
    async def preencher_com_dados_ia(
        self,
        cliente_id: UUID,
        dados_ia: ClienteFromDocumentAI,
    ) -> Cliente | None:
        """
        Preenche dados do cliente com informações extraídas pela IA.
        
        Apenas preenche campos vazios, não sobrescreve dados existentes.
        """
        cliente = await self._repo.get_by_id(cliente_id)
        if not cliente:
            return None
        
        # Mapeia campos do schema IA para o modelo Cliente
        campos_mapeados = {
            "nome": dados_ia.nome,
            "cpf": dados_ia.cpf,
            "rg": dados_ia.rg,
            "rg_orgao_emissor": dados_ia.rg_orgao_emissor,
            "rg_data_emissao": dados_ia.rg_data_emissao,
            "data_nascimento": dados_ia.data_nascimento,
            "sexo": dados_ia.sexo,
            "nome_mae": dados_ia.nome_mae,
            "nome_pai": dados_ia.nome_pai,
            "naturalidade": dados_ia.naturalidade,
        }
        
        # Atualiza apenas campos vazios no cliente
        update_data = {}
        for campo, valor in campos_mapeados.items():
            if valor and not getattr(cliente, campo, None):
                update_data[campo] = valor
        
        if update_data:
            return await self._repo.update(cliente_id, **update_data)
        
        return cliente
