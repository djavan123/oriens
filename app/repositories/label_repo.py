# app/repositories/label_repo.py
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label


class LabelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_by_user(self, user_id: int) -> list[Label]:
        result = await self.db.execute(
            select(Label).where(Label.user_id == user_id).order_by(Label.name)
        )
        return list(result.scalars().all())

    async def create(self, user_id: int, name: str, color: Optional[str] = None) -> Label:
        label = Label(user_id=user_id, name=name, color=color)
        self.db.add(label)
        await self.db.commit()
        await self.db.refresh(label)
        return label

    async def delete(self, label_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(Label).where(Label.id == label_id, Label.user_id == user_id)
        )
        label = result.scalar_one_or_none()
        if not label:
            return False
        await self.db.delete(label)
        await self.db.commit()
        return True
