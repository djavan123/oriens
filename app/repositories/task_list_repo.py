# app/repositories/task_list_repo.py
from typing import Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.task_list import TaskList

# (system_key, nome) das listas internas garantidas para todo usuário.
_SYSTEM_LISTS: list[tuple[str, str]] = [
    ("notes", "Notas"),
    ("repository", "Repositório"),
]


class TaskListRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_by_user(self, user_id: int) -> list[TaskList]:
        result = await self.db.execute(
            select(TaskList)
            .where(TaskList.user_id == user_id, TaskList.archived.is_(False))
            .order_by(TaskList.order_index.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, list_id: int, user_id: int) -> Optional[TaskList]:
        result = await self.db.execute(
            select(TaskList).where(TaskList.id == list_id, TaskList.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_system_list(self, user_id: int, system_key: str) -> Optional[TaskList]:
        result = await self.db.execute(
            select(TaskList).where(
                TaskList.user_id == user_id, TaskList.system_key == system_key
            )
        )
        return result.scalar_one_or_none()

    async def _next_order_index(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.max(TaskList.order_index)).where(TaskList.user_id == user_id)
        )
        max_idx = result.scalar_one_or_none()
        return (max_idx + 1) if max_idx is not None else 0

    async def ensure_system_lists(self, user_id: int) -> None:
        """Garante as listas internas (Notas/Repositório) do usuário. Idempotente.

        Se a lista já existir (mesmo arquivada), não recria nem duplica.
        """
        existing = await self.db.execute(
            select(TaskList.system_key).where(
                TaskList.user_id == user_id, TaskList.system_key.is_not(None)
            )
        )
        have = {row[0] for row in existing.all()}
        missing = [(key, name) for key, name in _SYSTEM_LISTS if key not in have]
        if not missing:
            return
        next_idx = await self._next_order_index(user_id)
        for key, name in missing:
            self.db.add(TaskList(user_id=user_id, name=name, system_key=key, order_index=next_idx))
            next_idx += 1
        await self.db.commit()

    async def create(self, user_id: int, name: str) -> Optional[TaskList]:
        name = (name or "").strip()
        if not name:
            return None
        next_idx = await self._next_order_index(user_id)
        task_list = TaskList(user_id=user_id, name=name, order_index=next_idx)
        self.db.add(task_list)
        await self.db.commit()
        await self.db.refresh(task_list)
        return task_list

    async def update_name(self, list_id: int, user_id: int, name: str) -> Optional[TaskList]:
        name = (name or "").strip()
        if not name:
            return None
        task_list = await self.get_by_id(list_id, user_id)
        # Listas internas (Notas/Repositório) não são renomeáveis nesta fase.
        if not task_list or task_list.system_key is not None:
            return None
        task_list.name = name
        await self.db.commit()
        await self.db.refresh(task_list)
        return task_list

    async def archive(self, list_id: int, user_id: int) -> bool:
        task_list = await self.get_by_id(list_id, user_id)
        if not task_list:
            return False
        task_list.archived = True
        await self.db.execute(
            update(Task).where(Task.list_id == list_id, Task.user_id == user_id).values(list_id=None)
        )
        await self.db.commit()
        return True
