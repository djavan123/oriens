# app/services/task_service.py
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, EnergyLevel
from app.models.project_timeline import TimelineEventType
from app.repositories.task_repo import TaskRepository
from app.repositories.project_timeline_repo import ProjectTimelineRepository
from app.utils.verb_validator import validate_starts_with_verb

_SCORE_FIELDS = ("financial_impact", "operational_risk", "strategic_impact", "task_urgency", "effort")


def _calc_score(**kw) -> float:
    return (
        kw.get("financial_impact", 0) * 10
        + kw.get("operational_risk", 0) * 9
        + kw.get("strategic_impact", 0) * 8
        + kw.get("task_urgency", 0) * 6
        - kw.get("effort", 0) * 4
    )


def _score_from_task(task: Task, overrides: dict) -> float:
    vals = {f: overrides.get(f, getattr(task, f, 0)) for f in _SCORE_FIELDS}
    return _calc_score(**vals)


class TaskVerbError(ValueError):
    def __init__(self, title: str, suggestions: list[str]):
        self.suggestions = suggestions
        first_word = title.strip().split()[0] if title.strip() else title
        super().__init__(f'"{first_word}" não parece um verbo no infinitivo.')


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TaskRepository(db)
        self.timeline = ProjectTimelineRepository(db)

    async def get_all(self, user_id: int, **filters) -> list[Task]:
        return await self.repo.get_all_by_user(user_id, **filters)

    async def get_by_id(self, task_id: int, user_id: int) -> Optional[Task]:
        return await self.repo.get_by_id(task_id, user_id)

    async def create(
        self,
        user_id: int,
        title: str,
        project_id: Optional[int] = None,
        energy: EnergyLevel = EnergyLevel.medium,
        is_quick_win: bool = False,
        **extra,
    ) -> Task:
        # Validação de verbo desativada (SCRIPT 12): qualquer título não vazio é aceito.
        # O helper validate_starts_with_verb continua disponível, apenas não é chamado.
        extra["priority_score"] = _calc_score(**extra)
        # Tarefas de topo num projeto recebem order_index = max+1 (append ao final).
        is_subtask = extra.get("parent_id") is not None
        if project_id is not None and not is_subtask:
            extra["order_index"] = await self.repo.get_max_order_index(project_id) + 1
        task = await self.repo.create(
            user_id=user_id,
            title=title,
            project_id=project_id,
            energy=energy,
            is_quick_win=is_quick_win,
            **extra,
        )
        if task.project_id:
            self.timeline.record(task.project_id, user_id, TimelineEventType.task_created,
                                 f'Tarefa "{task.title}" criada')
            await self.db.commit()
        return task

    async def mark_done(self, task_id: int, user_id: int) -> Optional[Task]:
        task = await self.repo.get_by_id(task_id, user_id)
        if not task:
            return None
        if task.project_id:
            self.timeline.record(task.project_id, user_id, TimelineEventType.task_done,
                                 f'Tarefa "{task.title}" concluída')
        return await self.repo.update(
            task, status=TaskStatus.done, done_at=datetime.utcnow()
        )

    async def mark_blocked(self, task_id: int, user_id: int) -> Optional[Task]:
        task = await self.repo.get_by_id(task_id, user_id)
        if not task:
            return None
        return await self.repo.update(task, status=TaskStatus.blocked)

    async def mark_pending(self, task_id: int, user_id: int) -> Optional[Task]:
        task = await self.repo.get_by_id(task_id, user_id)
        if not task:
            return None
        return await self.repo.update(task, status=TaskStatus.pending, done_at=None)

    async def archive(self, task_id: int, user_id: int) -> Optional[Task]:
        task = await self.repo.get_by_id(task_id, user_id)
        if not task:
            return None
        return await self.repo.update(task, archived=True)

    async def update(self, task_id: int, user_id: int, **kwargs) -> Optional[Task]:
        task = await self.repo.get_by_id(task_id, user_id)
        if not task:
            return None
        # Validação de verbo desativada (SCRIPT 12) — qualquer título não vazio é aceito.
        if any(f in kwargs for f in _SCORE_FIELDS):
            kwargs["priority_score"] = _score_from_task(task, kwargs)
        return await self.repo.update(task, **kwargs)
