from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CaptureInbox


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

    async def get_unprocessed(self, user_id: int) -> list[CaptureInbox]:
        result = await self.db.execute(
            select(CaptureInbox)
            .where(CaptureInbox.user_id == user_id, CaptureInbox.processed.is_(False))
            .order_by(CaptureInbox.created_at.desc())
        )
        return list(result.scalars().all())

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
