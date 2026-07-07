# app/services/dashboard_service.py
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import Task, EnergyLevel
from app.models.weekly_directive import WeeklyDirective

from app.repositories.project_repo import ProjectRepository
from app.repositories.task_repo import TaskRepository
from app.repositories.weekly_directive_repo import WeeklyDirectiveRepository
from app.services.weekly_directive_service import current_week_start
from app.utils.overload_detector import OverloadResult, calculate_overload


@dataclass
class DashboardData:
    overload: OverloadResult
    priority_tasks: list[Task]
    quick_wins: list[Task]
    blocked_tasks: list[Task]
    active_projects: list[Project]
    visibility_mode: str = "reduced"  # "full" | "reduced" | "minimal"
    weekly_directive: Optional[WeeklyDirective] = None


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.projects = ProjectRepository(db)
        self.tasks = TaskRepository(db)
        self.weekly = WeeklyDirectiveRepository(db)

    async def get_projects_in_focus(
        self, user_id: int, context_id: Optional[int] = None, limit: int = 3
    ) -> dict:
        """Projetos ativos (em andamento, não arquivados) com próxima ação operacional.

        Ordem = prioridade do projeto (estratégica). Cada item traz a próxima ação:
        primeira tarefa pendente em ordem manual, ou fallback proxima_acao. Projetos
        sem próxima ação não entram na lista — só são contados (revisão semanal depois).
        """
        projects = await self.projects.get_active_by_user(user_id, context_id=context_id)
        ids = [p.id for p in projects]
        next_tasks = (
            await self.tasks.next_pending_tasks_by_project(user_id, ids) if ids else {}
        )
        focus: list[dict] = []
        without_next = 0
        for p in projects:  # já ordenados por prioridade asc, criação desc
            nt = next_tasks.get(p.id)
            if nt is not None:
                focus.append({"project": p, "next_task": nt, "next_text": None})
            elif p.proxima_acao:
                focus.append({"project": p, "next_task": None, "next_text": p.proxima_acao})
            else:
                without_next += 1
        return {"focus": focus[:limit], "without_next_count": without_next}

    async def get_standalone_tasks(
        self,
        user_id: int,
        energy: Optional[EnergyLevel] = None,
        context_id: Optional[int] = None,
        limit: int = 3,
    ) -> list[Task]:
        """Tarefas avulsas (project_id nulo) ordenadas pelas regras de prioridade."""
        return await self.tasks.get_priority_pending(
            user_id, limit=limit, energy=energy, context_id=context_id, standalone_only=True
        )

    @staticmethod
    def pick_now_action(projects_focus: dict, standalone_tasks: list[Task]) -> Optional[dict]:
        """Escolhe a ÚNICA ação dominante do bloco "Agora".

        Ordem: 1) próxima ação do primeiro projeto executável em foco;
               2) primeira tarefa avulsa prioritária. None se não houver nada.
        """
        focus = projects_focus.get("focus") if projects_focus else None
        if focus:
            item = focus[0]
            if item["next_task"] is not None:
                return {"kind": "project_task", "task": item["next_task"], "project": item["project"]}
            return {"kind": "project_fallback", "text": item["next_text"], "project": item["project"]}
        if standalone_tasks:
            return {"kind": "standalone", "task": standalone_tasks[0]}
        return None

    async def get_dashboard_data(
        self,
        user_id: int,
        energy_filter: Optional[EnergyLevel] = None,
        context_id: Optional[int] = None,
        cognitive_filter: Optional[str] = None,
    ) -> DashboardData:
        active_projects = await self.projects.get_active_by_user(user_id)
        pending_count = await self.tasks.count_pending(user_id)

        overload = calculate_overload(
            active_projects=len(active_projects),
            pending_tasks=pending_count,
        )

        if energy_filter == EnergyLevel.low:
            priority_tasks = []
            quick_wins = await self.tasks.get_quick_wins(user_id, context_id=context_id)
            visibility_mode = "minimal"
        elif energy_filter == EnergyLevel.high:
            priority_tasks = await self.tasks.get_priority_pending(
                user_id, limit=5, energy=energy_filter, context_id=context_id, cognitive_filter=cognitive_filter
            )
            quick_wins = await self.tasks.get_quick_wins(user_id, energy=energy_filter, context_id=context_id)
            visibility_mode = "full"
        else:
            priority_tasks = await self.tasks.get_priority_pending(
                user_id, limit=3, energy=energy_filter, context_id=context_id, cognitive_filter=cognitive_filter
            )
            quick_wins = await self.tasks.get_quick_wins(user_id, energy=energy_filter, context_id=context_id)
            visibility_mode = "reduced"

        blocked_tasks = await self.tasks.get_blocked(user_id, context_id=context_id)
        weekly_directive = await self.weekly.get_by_week(user_id, current_week_start())

        return DashboardData(
            overload=overload,
            priority_tasks=priority_tasks,
            quick_wins=quick_wins,
            blocked_tasks=blocked_tasks,
            active_projects=active_projects,
            visibility_mode=visibility_mode,
            weekly_directive=weekly_directive,
        )
