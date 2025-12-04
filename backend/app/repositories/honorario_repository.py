"""
Repository de Honorários.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.honorario import (
    ContratoHonorario,
    ParcelaHonorario,
    StatusContrato,
    StatusParcela,
)
from app.repositories.base import MultiTenantRepository


class ContratoHonorarioRepository(MultiTenantRepository[ContratoHonorario]):
    """Repository para operações com Contrato de Honorário."""
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        super().__init__(ContratoHonorario, db, escritorio_id)
    
    async def get_by_cliente(
        self,
        cliente_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ContratoHonorario]:
        """Lista contratos de um cliente."""
        result = await self.db.execute(
            select(ContratoHonorario)
            .where(
                ContratoHonorario.escritorio_id == self.escritorio_id,
                ContratoHonorario.cliente_id == cliente_id,
            )
            .order_by(ContratoHonorario.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_processo(
        self,
        processo_id: UUID,
    ) -> ContratoHonorario | None:
        """Busca contrato de um processo específico."""
        result = await self.db.execute(
            select(ContratoHonorario).where(
                ContratoHonorario.escritorio_id == self.escritorio_id,
                ContratoHonorario.processo_id == processo_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_ativos(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ContratoHonorario]:
        """Lista contratos ativos."""
        result = await self.db.execute(
            select(ContratoHonorario)
            .where(
                ContratoHonorario.escritorio_id == self.escritorio_id,
                ContratoHonorario.status == StatusContrato.ATIVO,
            )
            .order_by(ContratoHonorario.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_stats(self) -> dict:
        """Retorna estatísticas financeiras."""
        # Total de contratos
        total = await self.db.execute(
            select(func.count())
            .select_from(ContratoHonorario)
            .where(ContratoHonorario.escritorio_id == self.escritorio_id)
        )
        
        # Valor total contratado
        valor_total = await self.db.execute(
            select(func.sum(ContratoHonorario.valor_total))
            .where(
                ContratoHonorario.escritorio_id == self.escritorio_id,
                ContratoHonorario.status.in_([StatusContrato.ATIVO, StatusContrato.CONCLUIDO]),
            )
        )
        
        # Por status
        por_status_result = await self.db.execute(
            select(ContratoHonorario.status, func.count())
            .where(ContratoHonorario.escritorio_id == self.escritorio_id)
            .group_by(ContratoHonorario.status)
        )
        por_status = {row[0].value: row[1] for row in por_status_result}
        
        # Por tipo
        por_tipo_result = await self.db.execute(
            select(ContratoHonorario.tipo, func.count())
            .where(ContratoHonorario.escritorio_id == self.escritorio_id)
            .group_by(ContratoHonorario.tipo)
        )
        por_tipo = {row[0].value: row[1] for row in por_tipo_result}
        
        return {
            "total_contratos": total.scalar_one(),
            "valor_total_contratado": valor_total.scalar_one() or Decimal("0"),
            "por_status": por_status,
            "por_tipo": por_tipo,
        }


class ParcelaHonorarioRepository(MultiTenantRepository[ParcelaHonorario]):
    """Repository para operações com Parcela de Honorário."""
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        super().__init__(ParcelaHonorario, db, escritorio_id)
    
    async def get_by_contrato(
        self,
        contrato_id: UUID,
    ) -> list[ParcelaHonorario]:
        """Lista parcelas de um contrato."""
        result = await self.db.execute(
            select(ParcelaHonorario)
            .where(
                ParcelaHonorario.escritorio_id == self.escritorio_id,
                ParcelaHonorario.contrato_id == contrato_id,
            )
            .order_by(ParcelaHonorario.numero_parcela)
        )
        return list(result.scalars().all())
    
    async def get_pendentes(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ParcelaHonorario]:
        """Lista parcelas pendentes."""
        result = await self.db.execute(
            select(ParcelaHonorario)
            .where(
                ParcelaHonorario.escritorio_id == self.escritorio_id,
                ParcelaHonorario.status == StatusParcela.PENDENTE,
            )
            .order_by(ParcelaHonorario.data_vencimento)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_atrasadas(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ParcelaHonorario]:
        """Lista parcelas atrasadas."""
        result = await self.db.execute(
            select(ParcelaHonorario)
            .where(
                ParcelaHonorario.escritorio_id == self.escritorio_id,
                ParcelaHonorario.status == StatusParcela.PENDENTE,
                ParcelaHonorario.data_vencimento < date.today(),
            )
            .order_by(ParcelaHonorario.data_vencimento)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_proximos_vencimentos(
        self,
        dias: int = 30,
        limit: int = 10,
    ) -> list[ParcelaHonorario]:
        """Lista próximas parcelas a vencer."""
        from datetime import timedelta
        
        data_limite = date.today() + timedelta(days=dias)
        
        result = await self.db.execute(
            select(ParcelaHonorario)
            .where(
                ParcelaHonorario.escritorio_id == self.escritorio_id,
                ParcelaHonorario.status == StatusParcela.PENDENTE,
                ParcelaHonorario.data_vencimento >= date.today(),
                ParcelaHonorario.data_vencimento <= data_limite,
            )
            .order_by(ParcelaHonorario.data_vencimento)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def registrar_pagamento(
        self,
        parcela_id: UUID,
        valor_pago: Decimal,
        data_pagamento: date,
        forma_pagamento: str,
        registrado_por_id: UUID,
        comprovante_path: str | None = None,
        observacoes: str | None = None,
    ) -> ParcelaHonorario | None:
        """Registra pagamento de uma parcela."""
        parcela = await self.get_by_id(parcela_id)
        if not parcela:
            return None
        
        await self.db.execute(
            update(ParcelaHonorario)
            .where(
                ParcelaHonorario.id == parcela_id,
                ParcelaHonorario.escritorio_id == self.escritorio_id,
            )
            .values(
                valor_pago=valor_pago,
                data_pagamento=data_pagamento,
                forma_pagamento=forma_pagamento,
                status=StatusParcela.PAGO,
                registrado_por_id=registrado_por_id,
                comprovante_path=comprovante_path,
                observacoes=observacoes,
            )
        )
        await self.db.commit()
        await self.db.refresh(parcela)
        return parcela
    
    async def atualizar_status_atrasadas(self) -> int:
        """Atualiza status de parcelas vencidas para ATRASADO."""
        result = await self.db.execute(
            update(ParcelaHonorario)
            .where(
                ParcelaHonorario.escritorio_id == self.escritorio_id,
                ParcelaHonorario.status == StatusParcela.PENDENTE,
                ParcelaHonorario.data_vencimento < date.today(),
            )
            .values(status=StatusParcela.ATRASADO)
        )
        await self.db.commit()
        return result.rowcount
    
    async def get_stats(self) -> dict:
        """Retorna estatísticas de parcelas."""
        # Total recebido
        total_recebido = await self.db.execute(
            select(func.sum(ParcelaHonorario.valor_pago))
            .where(
                ParcelaHonorario.escritorio_id == self.escritorio_id,
                ParcelaHonorario.status == StatusParcela.PAGO,
            )
        )
        
        # Total pendente
        total_pendente = await self.db.execute(
            select(func.sum(ParcelaHonorario.valor))
            .where(
                ParcelaHonorario.escritorio_id == self.escritorio_id,
                ParcelaHonorario.status.in_([StatusParcela.PENDENTE, StatusParcela.ATRASADO]),
            )
        )
        
        # Atrasadas
        atrasadas = await self.db.execute(
            select(func.count(), func.sum(ParcelaHonorario.valor))
            .select_from(ParcelaHonorario)
            .where(
                ParcelaHonorario.escritorio_id == self.escritorio_id,
                ParcelaHonorario.status == StatusParcela.ATRASADO,
            )
        )
        atrasadas_row = atrasadas.first()
        
        return {
            "valor_total_recebido": total_recebido.scalar_one() or Decimal("0"),
            "valor_total_pendente": total_pendente.scalar_one() or Decimal("0"),
            "parcelas_atrasadas": atrasadas_row[0] if atrasadas_row else 0,
            "valor_atrasado": atrasadas_row[1] or Decimal("0") if atrasadas_row else Decimal("0"),
        }
    
    async def get_pagas_mes_atual(self) -> list[ParcelaHonorario]:
        """Lista parcelas pagas no mês atual."""
        from datetime import datetime
        
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)
        
        result = await self.db.execute(
            select(ParcelaHonorario)
            .where(
                ParcelaHonorario.escritorio_id == self.escritorio_id,
                ParcelaHonorario.status == StatusParcela.PAGO,
                ParcelaHonorario.data_pagamento >= primeiro_dia,
                ParcelaHonorario.data_pagamento <= hoje,
            )
            .order_by(ParcelaHonorario.data_pagamento.desc())
        )
        return list(result.scalars().all())
