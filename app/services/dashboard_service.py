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
        self.projects = ProjectRepository(db)
        self.tasks = TaskRepository(db)
        self.weekly = WeeklyDirectiveRepository(db)

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
