"""
Repository de Notificações.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notificacao import (
    CanalNotificacao,
    Notificacao,
    PreferenciaNotificacao,
    StatusNotificacao,
    TipoNotificacao,
)
from app.repositories.base import MultiTenantRepository


class NotificacaoRepository(MultiTenantRepository[Notificacao]):
    """Repository para operações com Notificação."""
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        super().__init__(Notificacao, db, escritorio_id)
    
    async def get_by_usuario(
        self,
        usuario_id: UUID,
        apenas_nao_lidas: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notificacao]:
        """Lista notificações de um usuário."""
        query = select(Notificacao).where(
            Notificacao.escritorio_id == self.escritorio_id,
            Notificacao.usuario_id == usuario_id,
        )
        
        if apenas_nao_lidas:
            query = query.where(Notificacao.status != StatusNotificacao.LIDA)
        
        result = await self.db.execute(
            query.order_by(Notificacao.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_nao_lidas(self, usuario_id: UUID) -> int:
        """Conta notificações não lidas de um usuário."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Notificacao)
            .where(
                Notificacao.escritorio_id == self.escritorio_id,
                Notificacao.usuario_id == usuario_id,
                Notificacao.status != StatusNotificacao.LIDA,
            )
        )
        return result.scalar_one()
    
    async def marcar_como_lida(
        self,
        notificacao_ids: list[UUID],
        usuario_id: UUID,
    ) -> int:
        """Marca notificações como lidas."""
        result = await self.db.execute(
            update(Notificacao)
            .where(
                Notificacao.id.in_(notificacao_ids),
                Notificacao.escritorio_id == self.escritorio_id,
                Notificacao.usuario_id == usuario_id,
            )
            .values(
                status=StatusNotificacao.LIDA,
                lida_em=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()
        return result.rowcount
    
    async def marcar_todas_como_lidas(self, usuario_id: UUID) -> int:
        """Marca todas as notificações de um usuário como lidas."""
        result = await self.db.execute(
            update(Notificacao)
            .where(
                Notificacao.escritorio_id == self.escritorio_id,
                Notificacao.usuario_id == usuario_id,
                Notificacao.status != StatusNotificacao.LIDA,
            )
            .values(
                status=StatusNotificacao.LIDA,
                lida_em=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()
        return result.rowcount
    
    async def get_pendentes_envio(
        self,
        canal: CanalNotificacao | None = None,
        limit: int = 100,
    ) -> list[Notificacao]:
        """Lista notificações pendentes de envio."""
        query = select(Notificacao).where(
            Notificacao.status == StatusNotificacao.PENDENTE,
        )
        
        if canal:
            query = query.where(Notificacao.canal == canal)
        
        # Agendadas para agora ou antes
        query = query.where(
            (Notificacao.agendada_para == None) |  # noqa: E711
            (Notificacao.agendada_para <= datetime.now(timezone.utc))
        )
        
        result = await self.db.execute(
            query.order_by(Notificacao.created_at).limit(limit)
        )
        return list(result.scalars().all())
    
    async def atualizar_status_envio(
        self,
        notificacao_id: UUID,
        status: StatusNotificacao,
        erro: str | None = None,
    ) -> None:
        """Atualiza status de envio da notificação."""
        update_data = {
            "status": status,
            "tentativas": Notificacao.tentativas + 1,
        }
        
        if status == StatusNotificacao.ENVIADA:
            update_data["enviada_em"] = datetime.now(timezone.utc)
        elif status == StatusNotificacao.FALHA and erro:
            update_data["erro_envio"] = erro
        
        await self.db.execute(
            update(Notificacao)
            .where(Notificacao.id == notificacao_id)
            .values(**update_data)
        )
        await self.db.commit()
    
    async def get_stats(self, usuario_id: UUID) -> dict:
        """Retorna estatísticas de notificações do usuário."""
        # Total
        total = await self.db.execute(
            select(func.count())
            .select_from(Notificacao)
            .where(
                Notificacao.escritorio_id == self.escritorio_id,
                Notificacao.usuario_id == usuario_id,
            )
        )
        
        # Não lidas
        nao_lidas = await self.count_nao_lidas(usuario_id)
        
        # Por tipo
        por_tipo_result = await self.db.execute(
            select(Notificacao.tipo, func.count())
            .where(
                Notificacao.escritorio_id == self.escritorio_id,
                Notificacao.usuario_id == usuario_id,
            )
            .group_by(Notificacao.tipo)
        )
        por_tipo = {row[0].value: row[1] for row in por_tipo_result}
        
        return {
            "total": total.scalar_one(),
            "nao_lidas": nao_lidas,
            "por_tipo": por_tipo,
        }


class PreferenciaNotificacaoRepository(MultiTenantRepository[PreferenciaNotificacao]):
    """Repository para preferências de notificação."""
    
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        super().__init__(PreferenciaNotificacao, db, escritorio_id)
    
    async def get_by_usuario(self, usuario_id: UUID) -> PreferenciaNotificacao | None:
        """Busca preferências de um usuário."""
        result = await self.db.execute(
            select(PreferenciaNotificacao).where(
                PreferenciaNotificacao.escritorio_id == self.escritorio_id,
                PreferenciaNotificacao.usuario_id == usuario_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_or_create(self, usuario_id: UUID) -> PreferenciaNotificacao:
        """Busca ou cria preferências padrão para um usuário."""
        pref = await self.get_by_usuario(usuario_id)
        
        if pref is None:
            pref = await self.create(usuario_id=usuario_id)
        
        return pref
    
    async def atualizar_fcm_token(
        self,
        usuario_id: UUID,
        fcm_token: str,
    ) -> None:
        """Atualiza o FCM token do usuário."""
        await self.db.execute(
            update(PreferenciaNotificacao)
            .where(
                PreferenciaNotificacao.escritorio_id == self.escritorio_id,
                PreferenciaNotificacao.usuario_id == usuario_id,
            )
            .values(fcm_token=fcm_token)
        )
        await self.db.commit()
