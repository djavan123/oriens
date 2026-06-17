from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, CognitiveLoad, EnergyLevel

_COGNITIVE_MAP: dict[str, list[CognitiveLoad]] = {
    "morning":    [CognitiveLoad.deep, CognitiveLoad.high],
    "afternoon":  [CognitiveLoad.medium],
    "end_of_day": [CognitiveLoad.low],
}

_energy_order = case(
    (Task.energy == EnergyLevel.high, 1),
    (Task.energy == EnergyLevel.medium, 2),
    (Task.energy == EnergyLevel.low, 3),
    else_=4,
)


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _apply_context(self, q, context_id: Optional[int]):
        if context_id is not None:
            q = q.where(
                (Task.context_id.is_(None)) | (Task.context_id == context_id)
            )
        return q

    def _apply_cognitive(self, q, cognitive_filter: Optional[str]):
        if cognitive_filter and cognitive_filter in _COGNITIVE_MAP:
            q = q.where(Task.cognitive_load.in_(_COGNITIVE_MAP[cognitive_filter]))
        return q

    async def get_priority_pending(
        self,
        user_id: int,
        limit: int = 3,
        energy: Optional[EnergyLevel] = None,
        context_id: Optional[int] = None,
        cognitive_filter: Optional[str] = None,
    ) -> list[Task]:
        q = select(Task).where(Task.user_id == user_id, Task.status == TaskStatus.pending, Task.archived.is_(False), Task.parent_id.is_(None))
        if energy is not None:
            q = q.where(Task.energy == energy)
        q = self._apply_context(q, context_id)
        q = self._apply_cognitive(q, cognitive_filter)
        result = await self.db.execute(
            q.order_by(Task.priority_score.desc(), _energy_order, Task.created_at.asc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_quick_wins(
        self,
        user_id: int,
        energy: Optional[EnergyLevel] = None,
        context_id: Optional[int] = None,
    ) -> list[Task]:
        q = select(Task).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.pending,
            Task.is_quick_win.is_(True),
            Task.archived.is_(False),
            Task.parent_id.is_(None),
        )
        if energy is not None:
            q = q.where(Task.energy == energy)
        q = self._apply_context(q, context_id)
        result = await self.db.execute(
            q.order_by(Task.priority_score.desc(), _energy_order, Task.created_at.asc()).limit(5)
        )
        return list(result.scalars().all())

    async def get_blocked(self, user_id: int, context_id: Optional[int] = None) -> list[Task]:
        q = select(Task).where(Task.user_id == user_id, Task.status == TaskStatus.blocked, Task.archived.is_(False), Task.parent_id.is_(None))
        q = self._apply_context(q, context_id)
        result = await self.db.execute(q.order_by(Task.created_at.desc()))
        return list(result.scalars().all())

    async def get_all_by_user(
        self,
        user_id: int,
        project_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        energy: Optional[EnergyLevel] = None,
        include_subtasks: bool = False,
    ) -> list[Task]:
        q = select(Task).where(Task.user_id == user_id, Task.archived.is_(False))
        if not include_subtasks:
            q = q.where(Task.parent_id.is_(None))
        if project_id is not None:
            q = q.where(Task.project_id == project_id)
        if status is not None:
            q = q.where(Task.status == status)
        if energy is not None:
            q = q.where(Task.energy == energy)
        result = await self.db.execute(q.order_by(Task.priority_score.desc(), _energy_order, Task.created_at.asc()))
        return list(result.scalars().all())

    async def get_children_map(self, user_id: int, parent_ids: list[int]) -> dict[int, list[Task]]:
        """Retorna {parent_id: [subtarefas]} para renderizar aninhado no detalhe."""
        if not parent_ids:
            return {}
        result = await self.db.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.archived.is_(False),
                Task.parent_id.in_(parent_ids),
            )
            .order_by(Task.created_at.asc())
        )
        children: dict[int, list[Task]] = {}
        for task in result.scalars().all():
            children.setdefault(task.parent_id, []).append(task)
        return children

    async def get_by_id(self, task_id: int, user_id: int) -> Optional[Task]:
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def progress_by_project(
        self, user_id: int, project_ids: list[int]
    ) -> dict[int, tuple[int, int]]:
        """Retorna {project_id: (done, total)} contando tarefas não-arquivadas.
        Uma única query agregada para evitar N+1 na listagem de projetos."""
        if not project_ids:
            return {}
        done_expr = func.sum(
            case((Task.status == TaskStatus.done, 1), else_=0)
        )
        result = await self.db.execute(
            select(Task.project_id, func.count(), done_expr)
            .where(
                Task.user_id == user_id,
                Task.project_id.in_(project_ids),
                Task.archived.is_(False),
            )
            .group_by(Task.project_id)
        )
        return {row[0]: (int(row[2] or 0), int(row[1])) for row in result.all()}

    async def overdue_by_project(
        self, user_id: int, project_ids: list[int]
    ) -> dict[int, int]:
        """Retorna {project_id: nº de tarefas atrasadas} (prazo no passado, não concluídas)."""
        if not project_ids:
            return {}
        today = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Task.project_id, func.count())
            .where(
                Task.user_id == user_id,
                Task.project_id.in_(project_ids),
                Task.archived.is_(False),
                Task.status != TaskStatus.done,
                Task.deadline.is_not(None),
                Task.deadline < today,
            )
            .group_by(Task.project_id)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def count_pending(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Task)
            .where(Task.user_id == user_id, Task.status == TaskStatus.pending, Task.archived.is_(False), Task.parent_id.is_(None))
        )
        return result.scalar_one()

    async def create(self, user_id: int, **kwargs) -> Task:
        task = Task(user_id=user_id, **kwargs)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def update(self, task: Task, **kwargs) -> Task:
        if "status" in kwargs and kwargs["status"] == TaskStatus.done:
            kwargs.setdefault("done_at", datetime.now(timezone.utc))
        for key, value in kwargs.items():
            setattr(task, key, value)
        await self.db.commit()
        await self.db.refresh(task)
        return task
