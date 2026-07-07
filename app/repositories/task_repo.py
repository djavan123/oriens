from datetime import date
from typing import Optional
from sqlalchemy import case, func, nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, CognitiveLoad, EnergyLevel
from app.models.project_section import ProjectSection
from app.utils.time import utcnow


def _urgency_rank(task: Task) -> int:
    """0 = atrasado, 1 = hoje, 2 = resto (futuro ou sem prazo)."""
    if not task.deadline:
        return 2
    d = task.deadline.date()
    today = date.today()
    if d < today:
        return 0
    if d == today:
        return 1
    return 2


def _priority_sort_key(task: Task):
    # Urgência primeiro; dentro do grupo, importância desc; desempate por score e criação.
    return (_urgency_rank(task), -task.importancia, -task.priority_score, task.created_at)


def _project_task_order():
    """Ordem de tarefas de projeto: seção → order_index manual → criação."""
    return [
        nullslast(ProjectSection.order_index.asc()),
        nullslast(Task.order_index.asc()),
        Task.created_at.asc(),
    ]

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
        standalone_only: bool = False,
    ) -> list[Task]:
        q = select(Task).where(Task.user_id == user_id, Task.status == TaskStatus.pending, Task.archived.is_(False), Task.parent_id.is_(None))
        if standalone_only:
            q = q.where(Task.project_id.is_(None))
        if energy is not None:
            q = q.where(Task.energy == energy)
        q = self._apply_context(q, context_id)
        q = self._apply_cognitive(q, cognitive_filter)
        result = await self.db.execute(
            q.order_by(Task.priority_score.desc(), _energy_order, Task.created_at.asc())
        )
        tasks = list(result.scalars().all())
        # Reordena por urgência (atrasado→hoje→resto) e, dentro do grupo, por importância.
        tasks.sort(key=_priority_sort_key)
        return tasks[:limit]

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
        # Tarefas de projeto: seção → order_index. Avulsas: por score/energia.
        if project_id is not None:
            q = q.outerjoin(ProjectSection, Task.section_id == ProjectSection.id)
            order = _project_task_order()
        else:
            order = [Task.priority_score.desc(), _energy_order, Task.created_at.asc()]
        result = await self.db.execute(q.order_by(*order))
        return list(result.scalars().all())

    async def get_standalone_tasks(self, user_id: int, context_id: Optional[int] = None) -> list[Task]:
        """Tarefas avulsas pendentes (project_id IS NULL) para a página Listas."""
        q = select(Task).where(
            Task.user_id == user_id,
            Task.project_id.is_(None),
            Task.parent_id.is_(None),
            Task.archived.is_(False),
            Task.status == TaskStatus.pending,
        ).order_by(Task.importancia.desc(), Task.created_at.desc())
        q = self._apply_context(q, context_id)
        result = await self.db.execute(q)
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
        today = utcnow()
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
            kwargs.setdefault("done_at", utcnow())
        for key, value in kwargs.items():
            setattr(task, key, value)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_project_next_task(self, project_id: int, user_id: int) -> Optional[Task]:
        """Primeira tarefa pendente de topo do projeto, em ordem seção → order_index."""
        result = await self.db.execute(
            select(Task)
            .outerjoin(ProjectSection, Task.section_id == ProjectSection.id)
            .where(
                Task.project_id == project_id,
                Task.user_id == user_id,
                Task.status == TaskStatus.pending,
                Task.archived.is_(False),
                Task.parent_id.is_(None),
            )
            .order_by(*_project_task_order())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_max_order_index(self, project_id: int) -> int:
        """Maior order_index atual entre tarefas de topo do projeto (-1 se nenhuma)."""
        result = await self.db.execute(
            select(func.max(Task.order_index))
            .where(Task.project_id == project_id, Task.parent_id.is_(None))
        )
        val = result.scalar_one_or_none()
        return val if val is not None else -1

    async def _load_reorderable_tasks(
        self, project_id: int, user_id: int, task_ids: list[int]
    ) -> Optional[dict[int, Task]]:
        """Carrega as tarefas de `task_ids` validando ownership, pertencimento ao
        projeto e que são tarefas de topo (sem subtarefas). None se algo falhar."""
        result = await self.db.execute(
            select(Task).where(Task.id.in_(task_ids), Task.user_id == user_id)
        )
        tasks = {t.id: t for t in result.scalars().all()}
        if len(tasks) != len(task_ids):
            return None
        if any(t.project_id != project_id or t.parent_id is not None for t in tasks.values()):
            return None
        return tasks

    async def reorder_project_tasks(
        self, project_id: int, user_id: int, task_ids: list[int]
    ) -> bool:
        """Persiste order_index na sequência dada. Retorna False se validação falhar."""
        if not task_ids:
            return False
        tasks = await self._load_reorderable_tasks(project_id, user_id, task_ids)
        if tasks is None:
            return False
        for idx, task_id in enumerate(task_ids):
            tasks[task_id].order_index = idx
        await self.db.commit()
        return True

    async def next_pending_tasks_by_project(
        self, user_id: int, project_ids: list[int]
    ) -> dict[int, Task]:
        """{project_id: primeira tarefa pendente de topo em ordem seção → order_index}."""
        if not project_ids:
            return {}
        result = await self.db.execute(
            select(Task)
            .outerjoin(ProjectSection, Task.section_id == ProjectSection.id)
            .where(
                Task.user_id == user_id,
                Task.project_id.in_(project_ids),
                Task.status == TaskStatus.pending,
                Task.archived.is_(False),
                Task.parent_id.is_(None),
            )
            .order_by(Task.project_id, *_project_task_order())
        )
        out: dict[int, Task] = {}
        for t in result.scalars().all():
            if t.project_id not in out:
                out[t.project_id] = t
        return out

    async def pending_count_by_project(
        self, user_id: int, project_ids: list[int]
    ) -> dict[int, int]:
        """{project_id: nº de tarefas pendentes de topo}."""
        if not project_ids:
            return {}
        result = await self.db.execute(
            select(Task.project_id, func.count())
            .where(
                Task.user_id == user_id,
                Task.project_id.in_(project_ids),
                Task.status == TaskStatus.pending,
                Task.archived.is_(False),
                Task.parent_id.is_(None),
            )
            .group_by(Task.project_id)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def reorder_section_tasks(
        self,
        project_id: int,
        user_id: int,
        section_id: Optional[int],
        task_ids: list[int],
    ) -> bool:
        """Atribui section_id e order_index (0, 1, 2…) às tarefas na sequência dada.

        Valida: ownership, pertencimento ao projeto, sem subtarefas.
        Retorna False se qualquer validação falhar.
        """
        if not task_ids:
            return True
        tasks = await self._load_reorderable_tasks(project_id, user_id, task_ids)
        if tasks is None:
            return False
        for idx, task_id in enumerate(task_ids):
            tasks[task_id].section_id = section_id
            tasks[task_id].order_index = idx
        await self.db.commit()
        return True
