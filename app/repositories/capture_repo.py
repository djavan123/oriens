from datetime import timedelta
from typing import Optional
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CaptureInbox
from app.utils.time import utcnow


class CaptureRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, content: str) -> CaptureInbox:
        item = CaptureInbox(user_id=user_id, content=content)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def get_by_id(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        result = await self.db.execute(
            select(CaptureInbox).where(
                CaptureInbox.id == capture_id, CaptureInbox.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    def _inbox_filter(self, q, user_id: int):
        return q.where(
            CaptureInbox.user_id == user_id,
            CaptureInbox.processed.is_(False),
            CaptureInbox.resolved_at.is_(None),
            CaptureInbox.discarded_at.is_(None),
        )

    async def get_inbox(
        self, user_id: int, limit: Optional[int] = None, offset: int = 0
    ) -> list[CaptureInbox]:
        """Itens pendentes: não processados, não resolvidos, não descartados.

        `limit`/`offset` habilitam a paginação "carregar mais" da Caixa de Entrada
        (o inbox cresce sem limite via captura por Telegram).
        """
        q = self._inbox_filter(select(CaptureInbox), user_id).order_by(
            CaptureInbox.created_at.desc()
        )
        if offset:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def count_inbox(self, user_id: int) -> int:
        result = await self.db.execute(
            self._inbox_filter(
                select(func.count()).select_from(CaptureInbox), user_id
            )
        )
        return result.scalar_one()

    async def get_unprocessed(self, user_id: int) -> list[CaptureInbox]:
        """Itens para o fluxo de Processar: mesma regra da caixa de entrada."""
        return await self.get_inbox(user_id)

    async def get_all(self, user_id: int) -> list[CaptureInbox]:
        result = await self.db.execute(
            select(CaptureInbox)
            .where(CaptureInbox.user_id == user_id)
            .order_by(CaptureInbox.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_processed(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        item = await self.get_by_id(capture_id, user_id)
        if not item:
            return None
        item.processed = True
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def resolve(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        item = await self.get_by_id(capture_id, user_id)
        if not item:
            return None
        item.resolved_at = utcnow()
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def discard_to_trash(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        item = await self.get_by_id(capture_id, user_id)
        if not item:
            return None
        item.discarded_at = utcnow()
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def get_trash(
        self, user_id: int, limit: Optional[int] = None, offset: int = 0
    ) -> list[CaptureInbox]:
        q = (
            select(CaptureInbox)
            .where(
                CaptureInbox.user_id == user_id,
                CaptureInbox.discarded_at.is_not(None),
            )
            .order_by(CaptureInbox.discarded_at.desc())
        )
        if offset:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def restore(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        item = await self.get_by_id(capture_id, user_id)
        if not item:
            return None
        item.discarded_at = None
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def cleanup_old_discarded(self, user_id: int) -> None:
        cutoff = utcnow() - timedelta(days=15)
        await self.db.execute(
            delete(CaptureInbox).where(
                CaptureInbox.user_id == user_id,
                CaptureInbox.discarded_at.is_not(None),
                CaptureInbox.discarded_at < cutoff,
            )
        )
        await self.db.commit()

    async def update_content(self, capture_id: int, user_id: int, content: str) -> Optional[CaptureInbox]:
        item = await self.get_by_id(capture_id, user_id)
        if not item:
            return None
        item.content = content.strip()
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def hard_delete(self, capture_id: int, user_id: int) -> None:
        await self.db.execute(
            delete(CaptureInbox).where(
                CaptureInbox.id == capture_id,
                CaptureInbox.user_id == user_id,
            )
        )
        await self.db.commit()
