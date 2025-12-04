"""
Service de Honorários.

Gerencia contratos, parcelas e pagamentos.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleError,
    ResourceNotFoundError,
)
from app.models.honorario import (
    ContratoHonorario,
    FormaPagamento,
    ParcelaHonorario,
    StatusContrato,
    StatusParcela,
    TipoHonorario,
)
from app.repositories.honorario_repository import (
    ContratoHonorarioRepository,
    ParcelaHonorarioRepository,
)
from app.schemas.honorario import (
    ContratoCreate,
    ContratoStats,
    ContratoUpdate,
    DashboardFinanceiro,
    ParcelaCreate,
    ParcelaRegistrarPagamento,
    ParcelaUpdate,
    ResumoFinanceiro,
)

logger = structlog.get_logger()


class HonorarioService:
    """
    Service para gestão financeira de honorários.
    
    Gerencia contratos, parcelas e controle de pagamentos.
    """
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        self._db = db
        self._escritorio_id = escritorio_id
        self._contrato_repo = ContratoHonorarioRepository(db, escritorio_id)
        self._parcela_repo = ParcelaHonorarioRepository(db, escritorio_id)
    
    # === CONTRATOS ===
    
    async def criar_contrato(
        self,
        dados: ContratoCreate,
    ) -> ContratoHonorario:
        """
        Cria novo contrato de honorários.
        
        Se tipo for PARCELADO, cria parcelas automaticamente.
        """
        contrato = await self._contrato_repo.create(
            **dados.model_dump(exclude={"gerar_parcelas"}),
            status=StatusContrato.RASCUNHO,
        )
        
        # Se for parcelado e gerar_parcelas=True, gera automaticamente
        if dados.gerar_parcelas and dados.tipo == TipoHonorario.PARCELADO and dados.numero_parcelas:
            await self._gerar_parcelas_automaticas(contrato, dados.numero_parcelas)
        
        logger.info(
            "Contrato de honorários criado",
            contrato_id=str(contrato.id),
            tipo=dados.tipo.value,
            valor_total=str(dados.valor_total),
        )
        
        return contrato
    
    async def buscar_contrato(
        self,
        contrato_id: UUID,
        with_parcelas: bool = False,
    ) -> ContratoHonorario:
        """Busca contrato por ID."""
        # Sempre usa get_by_id, pois parcelas são carregadas via lazy="selectin"
        contrato = await self._contrato_repo.get_by_id(contrato_id)
        
        if not contrato:
            raise ResourceNotFoundError("Contrato", contrato_id)
        
        return contrato
    
    async def listar_contratos_cliente(
        self,
        cliente_id: UUID,
    ) -> list[ContratoHonorario]:
        """Lista contratos de um cliente."""
        return await self._contrato_repo.get_by_cliente(cliente_id)
    
    async def listar_contratos_processo(
        self,
        processo_id: UUID,
    ) -> list[ContratoHonorario]:
        """Lista contratos de um processo."""
        return await self._contrato_repo.get_by_processo(processo_id)
    
    async def atualizar_contrato(
        self,
        contrato_id: UUID,
        dados: ContratoUpdate,
    ) -> ContratoHonorario:
        """Atualiza contrato de honorários."""
        contrato = await self.buscar_contrato(contrato_id)
        
        # Não permite alteração em contratos finalizados
        if contrato.status in [StatusContrato.CONCLUIDO, StatusContrato.CANCELADO]:
            raise BusinessRuleError(
                f"Contrato {contrato.status.value} não pode ser alterado"
            )
        
        contrato = await self._contrato_repo.update(
            contrato_id,
            **dados.model_dump(exclude_unset=True),
        )
        
        return contrato
    
    async def ativar_contrato(self, contrato_id: UUID) -> ContratoHonorario:
        """Ativa contrato (sai de rascunho)."""
        contrato = await self.buscar_contrato(contrato_id)
        
        if contrato.status != StatusContrato.RASCUNHO:
            raise BusinessRuleError("Apenas contratos em rascunho podem ser ativados")
        
        contrato = await self._contrato_repo.update(
            contrato_id,
            status=StatusContrato.ATIVO,
        )
        
        logger.info("Contrato ativado", contrato_id=str(contrato_id))
        return contrato
    
    async def cancelar_contrato(
        self,
        contrato_id: UUID,
        motivo: str,
    ) -> ContratoHonorario:
        """Cancela contrato de honorários."""
        contrato = await self.buscar_contrato(contrato_id)
        
        if contrato.status in [StatusContrato.CONCLUIDO, StatusContrato.CANCELADO]:
            raise BusinessRuleError(f"Contrato já está {contrato.status.value}")
        
        contrato = await self._contrato_repo.update(
            contrato_id,
            status=StatusContrato.CANCELADO,
            observacoes=(contrato.observacoes or "") + f"\nCancelado: {motivo}",
        )
        
        logger.info(
            "Contrato cancelado",
            contrato_id=str(contrato_id),
            motivo=motivo,
        )
        
        return contrato
    
    # === PARCELAS ===
    
    async def criar_parcela(
        self,
        dados: ParcelaCreate,
        contrato_id: UUID,
    ) -> ParcelaHonorario:
        """Cria nova parcela para contrato."""
        # Valida contrato
        contrato = await self.buscar_contrato(contrato_id)
        
        if contrato.status == StatusContrato.CANCELADO:
            raise BusinessRuleError("Não é possível criar parcelas em contrato cancelado")
        
        parcela = await self._parcela_repo.create(
            contrato_id=contrato_id,
            **dados.model_dump(),
        )
        
        logger.info(
            "Parcela criada",
            parcela_id=str(parcela.id),
            contrato_id=str(contrato_id),
            valor=str(dados.valor),
        )
        
        return parcela
    
    async def listar_parcelas_contrato(
        self,
        contrato_id: UUID,
    ) -> list[ParcelaHonorario]:
        """Lista parcelas de um contrato."""
        return await self._parcela_repo.get_by_contrato(contrato_id)
    
    async def listar_parcelas_vencidas(self) -> list[ParcelaHonorario]:
        """Lista parcelas vencidas não pagas."""
        return await self._parcela_repo.get_atrasadas()
    
    async def listar_parcelas_a_vencer(
        self,
        dias: int = 30,
    ) -> list[ParcelaHonorario]:
        """Lista parcelas que vencem nos próximos X dias."""
        return await self._parcela_repo.get_proximos_vencimentos(dias)
    
    async def registrar_pagamento(
        self,
        parcela_id: UUID,
        dados: ParcelaRegistrarPagamento,
    ) -> ParcelaHonorario:
        """
        Registra pagamento de uma parcela.
        
        Atualiza status para PAGA se valor total foi pago.
        """
        parcela = await self._parcela_repo.get_by_id(parcela_id)
        if not parcela:
            raise ResourceNotFoundError("Parcela", parcela_id)
        
        if parcela.status == StatusParcela.PAGO:
            raise BusinessRuleError("Parcela já está paga")
        
        if parcela.status == StatusParcela.CANCELADO:
            raise BusinessRuleError("Parcela cancelada não pode receber pagamento")
        
        # Calcula novo valor pago
        valor_pago_atual = parcela.valor_pago or Decimal("0")
        novo_valor_pago = valor_pago_atual + dados.valor_pago
        
        # Determina novo status (parcialmente pago mantém como pendente se não quitou)
        if novo_valor_pago >= parcela.valor:
            novo_status = StatusParcela.PAGO
        else:
            novo_status = StatusParcela.PENDENTE  # Mantém pendente até pagar totalmente
        
        parcela = await self._parcela_repo.update(
            parcela_id,
            valor_pago=novo_valor_pago,
            data_pagamento=dados.data_pagamento or datetime.now(timezone.utc),
            forma_pagamento=dados.forma_pagamento,
            comprovante_path=dados.comprovante_path,
            status=novo_status,
        )
        
        logger.info(
            "Pagamento registrado",
            parcela_id=str(parcela_id),
            valor_pago=str(dados.valor_pago),
            valor_total_pago=str(novo_valor_pago),
            novo_status=novo_status.value,
        )
        
        # Verifica se contrato foi quitado
        await self._verificar_quitacao_contrato(parcela.contrato_id)
        
        return parcela
    
    async def cancelar_parcela(
        self,
        parcela_id: UUID,
        motivo: str,
    ) -> ParcelaHonorario:
        """Cancela uma parcela."""
        parcela = await self._parcela_repo.get_by_id(parcela_id)
        if not parcela:
            raise ResourceNotFoundError("Parcela", parcela_id)
        
        if parcela.status == StatusParcela.PAGO:
            raise BusinessRuleError("Parcela já paga não pode ser cancelada")
        
        parcela = await self._parcela_repo.update(
            parcela_id,
            status=StatusParcela.CANCELADO,
            observacoes=(parcela.observacoes or "") + f"\nCancelada: {motivo}",
        )
        
        return parcela
    
    # === RELATÓRIOS FINANCEIROS ===
    
    async def get_dashboard_financeiro(self) -> DashboardFinanceiro:
        """Retorna dashboard financeiro do escritório."""
        # Resumo geral
        resumo = await self._calcular_resumo_financeiro()
        
        # Parcelas vencidas
        vencidas = await self._parcela_repo.get_atrasadas()
        
        # Parcelas a vencer (30 dias)
        a_vencer = await self._parcela_repo.get_proximos_vencimentos(30)
        
        # Recebimentos do mês - busca pagas do mês atual
        pagas = await self._parcela_repo.get_pagas_mes_atual()
        
        return DashboardFinanceiro(
            receita_mes_atual=sum(p.valor_pago or Decimal("0") for p in pagas),
            receita_mes_anterior=Decimal("0"),  # TODO: implementar busca mês anterior
            variacao_percentual=0.0,
            previsao_mes_atual=sum(p.valor for p in a_vencer),
            recebido_mes_atual=sum(p.valor_pago or Decimal("0") for p in pagas),
            total_atrasado=sum(p.valor - (p.valor_pago or Decimal("0")) for p in vencidas),
            parcelas_atrasadas=len(vencidas),
            proximos_vencimentos=[],  # Simplificado
            historico_mensal=[],  # TODO: implementar
        )
    
    async def get_resumo_financeiro_cliente(
        self,
        cliente_id: UUID,
    ) -> ResumoFinanceiro:
        """Retorna resumo financeiro de um cliente."""
        contratos = await self._contrato_repo.get_by_cliente(cliente_id)
        
        total_contratado = Decimal("0")
        total_pago = Decimal("0")
        total_pendente = Decimal("0")
        
        for contrato in contratos:
            if contrato.status == StatusContrato.CANCELADO:
                continue
            
            total_contratado += contrato.valor_total
            total_pago += contrato.valor_pago
            total_pendente += contrato.valor_pendente
        
        return ResumoFinanceiro(
            total_contratado=total_contratado,
            total_pago=total_pago,
            total_pendente=total_pendente,
            percentual_pago=float(
                (total_pago / total_contratado * 100)
                if total_contratado > 0
                else 0
            ),
        )
    
    # === MÉTODOS AUXILIARES ===
    
    async def _gerar_parcelas_automaticas(
        self,
        contrato: ContratoHonorario,
        numero_parcelas: int,
    ) -> None:
        """Gera parcelas automaticamente para contrato parcelado."""
        valor_parcela = contrato.valor_total / numero_parcelas
        data_base = contrato.data_inicio or date.today()
        
        for i in range(numero_parcelas):
            # Calcula data de vencimento (mensal)
            mes = data_base.month + i
            ano = data_base.year + (mes - 1) // 12
            mes = ((mes - 1) % 12) + 1
            dia = min(data_base.day, 28)  # Evita problemas com meses curtos
            
            data_vencimento = date(ano, mes, dia)
            
            await self._parcela_repo.create(
                contrato_id=contrato.id,
                numero=i + 1,
                valor=valor_parcela,
                data_vencimento=data_vencimento,
                status=StatusParcela.PENDENTE,
            )
        
        logger.info(
            "Parcelas geradas automaticamente",
            contrato_id=str(contrato.id),
            numero_parcelas=numero_parcelas,
            valor_parcela=str(valor_parcela),
        )
    
    async def _verificar_quitacao_contrato(self, contrato_id: UUID) -> None:
        """Verifica e atualiza status se contrato foi quitado."""
        contrato = await self.buscar_contrato(contrato_id, with_parcelas=True)
        
        if contrato.percentual_pago >= 100:
            await self._contrato_repo.update(
                contrato_id,
                status=StatusContrato.CONCLUIDO,
            )
            
            logger.info(
                "Contrato quitado",
                contrato_id=str(contrato_id),
            )
    
    async def _calcular_resumo_financeiro(self) -> ResumoFinanceiro:
        """Calcula resumo financeiro geral do escritório."""
        contratos = await self._contrato_repo.get_all()
        
        total_contratado = Decimal("0")
        total_pago = Decimal("0")
        total_pendente = Decimal("0")
        
        for contrato in contratos:
            if contrato.status == StatusContrato.CANCELADO:
                continue
            
            total_contratado += contrato.valor_total
            total_pago += contrato.valor_pago
            total_pendente += contrato.valor_pendente
        
        return ResumoFinanceiro(
            total_contratado=total_contratado,
            total_pago=total_pago,
            total_pendente=total_pendente,
            percentual_pago=float(
                (total_pago / total_contratado * 100)
                if total_contratado > 0
                else 0
            ),
        )
