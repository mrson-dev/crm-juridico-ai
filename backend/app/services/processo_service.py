"""
Service de Processos.

Gerencia processos, prazos e andamentos com regras de negócio.
"""

from datetime import date, datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleError,
    ProcessoArquivadoError,
    ResourceNotFoundError,
)
from app.models.processo import (
    Andamento,
    FaseProcessual,
    Prazo,
    Processo,
    StatusPrazo,
)
from app.repositories.processo_repository import (
    AndamentoRepository,
    PrazoRepository,
    ProcessoRepository,
)
from app.schemas.processo import (
    AndamentoCreate,
    PrazoCreate,
    PrazoUpdate,
    ProcessoCreate,
    ProcessoStats,
    ProcessoUpdate,
)

logger = structlog.get_logger()


class ProcessoService:
    """
    Service para operações com Processo.
    
    Gerencia todo o ciclo de vida do processo judicial/administrativo.
    """
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        self._db = db
        self._escritorio_id = escritorio_id
        self._processo_repo = ProcessoRepository(db, escritorio_id)
        self._prazo_repo = PrazoRepository(db, escritorio_id)
        self._andamento_repo = AndamentoRepository(db, escritorio_id)
    
    # === PROCESSOS ===
    
    async def criar_processo(self, dados: ProcessoCreate) -> Processo:
        """
        Cria novo processo.
        
        Valida número CNJ único e vincula ao cliente.
        """
        # Verifica se número CNJ já existe
        if dados.numero_cnj:
            existente = await self._processo_repo.get_by_numero_cnj(dados.numero_cnj)
            if existente:
                raise BusinessRuleError(
                    f"Já existe processo com número CNJ {dados.numero_cnj}"
                )
        
        processo = await self._processo_repo.create(
            **dados.model_dump(),
            fase=FaseProcessual.REQUERIMENTO_ADMINISTRATIVO,
        )
        
        logger.info(
            "Processo criado",
            processo_id=str(processo.id),
            numero=processo.numero_principal,
            tipo_beneficio=processo.tipo_beneficio.value,
        )
        
        return processo
    
    async def buscar_processo(
        self,
        processo_id: UUID,
        with_relations: bool = False,
    ) -> Processo:
        """Busca processo por ID."""
        if with_relations:
            processo = await self._processo_repo.get_by_id_with_relations(processo_id)
        else:
            processo = await self._processo_repo.get_by_id(processo_id)
        
        if not processo:
            raise ResourceNotFoundError("Processo", processo_id)
        
        return processo
    
    async def listar_processos(
        self,
        skip: int = 0,
        limit: int = 20,
        fase: FaseProcessual | None = None,
        cliente_id: UUID | None = None,
        include_archived: bool = False,
    ) -> list[Processo]:
        """Lista processos com filtros."""
        if fase:
            return await self._processo_repo.get_by_fase(fase)
        
        if cliente_id:
            return await self._processo_repo.get_by_cliente(
                cliente_id, include_archived
            )
        
        return await self._processo_repo.get_all(skip, limit)
    
    async def pesquisar_processos(self, query: str) -> list[Processo]:
        """Pesquisa processos por número ou objeto."""
        return await self._processo_repo.search(query)
    
    async def atualizar_processo(
        self,
        processo_id: UUID,
        dados: ProcessoUpdate,
    ) -> Processo:
        """
        Atualiza dados do processo.
        
        Não permite alterações em processos arquivados.
        """
        processo = await self.buscar_processo(processo_id)
        
        if processo.is_archived and not dados.is_archived:
            raise ProcessoArquivadoError(processo_id)
        
        update_data = dados.model_dump(exclude_unset=True)
        
        # Se mudou de fase, registra andamento automático
        if dados.fase and dados.fase != processo.fase:
            await self._registrar_mudanca_fase(processo, dados.fase)
        
        processo = await self._processo_repo.update(processo_id, **update_data)
        
        logger.info(
            "Processo atualizado",
            processo_id=str(processo_id),
            campos=list(update_data.keys()),
        )
        
        return processo
    
    async def arquivar_processo(self, processo_id: UUID) -> Processo:
        """Arquiva processo encerrado."""
        processo = await self.buscar_processo(processo_id)
        
        if processo.is_archived:
            return processo
        
        processo = await self._processo_repo.update(
            processo_id,
            is_archived=True,
        )
        
        logger.info("Processo arquivado", processo_id=str(processo_id))
        return processo
    
    async def get_stats(self) -> ProcessoStats:
        """Retorna estatísticas dos processos."""
        stats = await self._processo_repo.get_stats()
        prazos_pendentes = await self._prazo_repo.count_pendentes()
        prazos_urgentes = await self._prazo_repo.count_urgentes()
        
        return ProcessoStats(
            total=stats["total"],
            por_fase=stats["por_fase"],
            por_tipo_beneficio=stats["por_tipo_beneficio"],
            prazos_pendentes=prazos_pendentes,
            prazos_urgentes=prazos_urgentes,
        )
    
    # === PRAZOS ===
    
    async def criar_prazo(self, dados: PrazoCreate) -> Prazo:
        """
        Cria novo prazo processual.
        
        ⚠️ Prazos são críticos - perda pode causar danos ao cliente.
        """
        # Valida que processo existe
        processo = await self.buscar_processo(dados.processo_id)
        
        if processo.is_archived:
            raise ProcessoArquivadoError(dados.processo_id)
        
        prazo = await self._prazo_repo.create(**dados.model_dump())
        
        logger.info(
            "Prazo criado",
            prazo_id=str(prazo.id),
            processo_id=str(dados.processo_id),
            data_fatal=str(dados.data_fatal),
            dias_restantes=prazo.dias_restantes,
        )
        
        # TODO: Agendar notificações para este prazo
        
        return prazo
    
    async def listar_prazos_pendentes(
        self,
        dias_futuros: int = 30,
    ) -> list[Prazo]:
        """Lista prazos pendentes do escritório."""
        return await self._prazo_repo.get_pendentes(dias_futuros)
    
    async def listar_prazos_urgentes(self, dias: int = 3) -> list[Prazo]:
        """Lista prazos que vencem em até X dias."""
        return await self._prazo_repo.get_urgentes(dias)
    
    async def listar_prazos_vencidos(self) -> list[Prazo]:
        """Lista prazos vencidos não cumpridos."""
        return await self._prazo_repo.get_vencidos()
    
    async def atualizar_prazo(
        self,
        prazo_id: UUID,
        dados: PrazoUpdate,
    ) -> Prazo:
        """Atualiza dados do prazo."""
        prazo = await self._prazo_repo.get_by_id(prazo_id)
        if not prazo:
            raise ResourceNotFoundError("Prazo", prazo_id)
        
        prazo = await self._prazo_repo.update(
            prazo_id,
            **dados.model_dump(exclude_unset=True),
        )
        
        return prazo
    
    async def cumprir_prazo(
        self,
        prazo_id: UUID,
        usuario_id: UUID,
    ) -> Prazo:
        """Marca prazo como cumprido."""
        prazo = await self._prazo_repo.get_by_id(prazo_id)
        if not prazo:
            raise ResourceNotFoundError("Prazo", prazo_id)
        
        if prazo.status != StatusPrazo.PENDENTE:
            raise BusinessRuleError(f"Prazo já está {prazo.status.value}")
        
        prazo = await self._prazo_repo.update(
            prazo_id,
            status=StatusPrazo.CUMPRIDO,
            data_cumprimento=datetime.now(timezone.utc),
            cumprido_por_id=usuario_id,
        )
        
        logger.info(
            "Prazo cumprido",
            prazo_id=str(prazo_id),
            cumprido_por=str(usuario_id),
        )
        
        return prazo
    
    # === ANDAMENTOS ===
    
    async def criar_andamento(
        self,
        dados: AndamentoCreate,
        registrado_por_id: UUID,
    ) -> Andamento:
        """Registra novo andamento processual."""
        # Valida que processo existe
        processo = await self.buscar_processo(dados.processo_id)
        
        if processo.is_archived:
            raise ProcessoArquivadoError(dados.processo_id)
        
        andamento = await self._andamento_repo.create(
            **dados.model_dump(),
            registrado_por_id=registrado_por_id,
        )
        
        logger.info(
            "Andamento registrado",
            andamento_id=str(andamento.id),
            processo_id=str(dados.processo_id),
        )
        
        return andamento
    
    async def listar_andamentos(
        self,
        processo_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Andamento]:
        """Lista andamentos de um processo."""
        return await self._andamento_repo.get_by_processo(processo_id, skip, limit)
    
    async def listar_andamentos_recentes(self, dias: int = 7) -> list[Andamento]:
        """Lista andamentos recentes do escritório."""
        return await self._andamento_repo.get_recentes(dias)
    
    # === MÉTODOS AUXILIARES ===
    
    async def _registrar_mudanca_fase(
        self,
        processo: Processo,
        nova_fase: FaseProcessual,
    ) -> None:
        """Registra andamento automático de mudança de fase."""
        andamento = await self._andamento_repo.create(
            processo_id=processo.id,
            data=datetime.now(timezone.utc),
            descricao=f"Processo movido para fase: {nova_fase.value}",
            fonte="sistema",
            gera_prazo=False,
        )
        
        logger.info(
            "Mudança de fase registrada",
            processo_id=str(processo.id),
            fase_anterior=processo.fase.value,
            nova_fase=nova_fase.value,
        )
