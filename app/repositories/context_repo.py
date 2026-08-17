# app/repositories/context_repo.py
from typing import Optional
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context import Context, ContextType
from app.models.project import Project
from app.models.task import Task
from app.models.task_list import TaskList


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
        # Contexto próprio OU padrão (user_id NULL, compartilhado) — o padrão nunca
        # bate em "== user_id", então sem o OR nenhum usuário conseguia excluí-lo.
        result = await self.db.execute(
            select(Context).where(
                Context.id == context_id,
                or_(Context.user_id.is_(None), Context.user_id == user_id),
            )
        )
        ctx = result.scalar_one_or_none()
        if not ctx:
            return False

        # SQLite não roda com PRAGMA foreign_keys=ON neste projeto, então o
        # ondelete="SET NULL" dos models não é garantido em runtime — limpeza
        # manual, mesmo padrão defensivo que TaskListRepository.archive() já usa.
        lists = await self.db.execute(
            select(TaskList.id).where(TaskList.context_id == context_id, TaskList.archived.is_(False))
        )
        list_ids = [row[0] for row in lists.all()]
        for list_id in list_ids:
            await self.db.execute(update(TaskList).where(TaskList.id == list_id).values(archived=True))
            await self.db.execute(
                update(Task).where(Task.list_id == list_id).values(list_id=None, context_id=None)
            )
        await self.db.execute(update(Task).where(Task.context_id == context_id).values(context_id=None))
        await self.db.execute(update(Project).where(Project.context_id == context_id).values(context_id=None))

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
