# app/repositories/context_repo.py
from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context import Context, ContextType


class ContextRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[Context]:
        result = await self.db.execute(select(Context).order_by(Context.id))
        return list(result.scalars().all())

    async def get_all_by_user(self, user_id: int) -> list[Context]:
        result = await self.db.execute(
            select(Context)
            .where(or_(Context.user_id.is_(None), Context.user_id == user_id))
            .order_by(Context.id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, context_id: int) -> Optional[Context]:
        result = await self.db.execute(select(Context).where(Context.id == context_id))
        return result.scalar_one_or_none()

    async def get_by_type(self, context_type: ContextType) -> Optional[Context]:
        result = await self.db.execute(
            select(Context).where(Context.type == context_type.value)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, name: str) -> Context:
        ctx = Context(user_id=user_id, name=name)
        self.db.add(ctx)
        await self.db.commit()
        await self.db.refresh(ctx)
        return ctx

    async def delete(self, context_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(Context).where(Context.id == context_id, Context.user_id == user_id)
        )
        ctx = result.scalar_one_or_none()
        if not ctx:
            return False
        await self.db.delete(ctx)
        await self.db.commit()
        return True

    async def seed_defaults(self) -> None:
        existing = await self.get_all()
        if existing:
            return
        defaults = [
            Context(name="Trabalho",     type=ContextType.work.value),
            Context(name="Recuperação",  type=ContextType.home_recovery.value),
            Context(name="Casa",         type=ContextType.home_operational.value),
            Context(name="Academia",     type=ContextType.gym.value),
        ]
        self.db.add_all(defaults)
        await self.db.commit()
