from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import RepositoryItem


class RepositoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, content: str) -> RepositoryItem:
        item = RepositoryItem(user_id=user_id, content=content)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def get_by_id(self, item_id: int, user_id: int) -> Optional[RepositoryItem]:
        result = await self.db.execute(
            select(RepositoryItem).where(
                RepositoryItem.id == item_id, RepositoryItem.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(self, user_id: int) -> list[RepositoryItem]:
        result = await self.db.execute(
            select(RepositoryItem)
            .where(RepositoryItem.user_id == user_id)
            .order_by(RepositoryItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, item_id: int, user_id: int) -> None:
        await self.db.execute(
            delete(RepositoryItem).where(
                RepositoryItem.id == item_id, RepositoryItem.user_id == user_id
            )
        )
        await self.db.commit()
