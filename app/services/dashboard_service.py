# app/services/dashboard_service.py
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, EnergyLevel

from app.repositories.project_repo import ProjectRepository
from app.repositories.task_repo import TaskRepository


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.projects = ProjectRepository(db)
        self.tasks = TaskRepository(db)

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

    async def get_evolution(self, user_id: int) -> dict:
        """Painel de evolução (progresso pessoal, GLOBAL — sem filtro de contexto):
        tarefas concluídas hoje + streak de dias consecutivos com >=1 conclusão."""
        done_today = await self.tasks.count_done_today(user_id)
        dates = await self.tasks.get_recent_completion_dates(user_id)
        return {"done_today": done_today, "streak": self._compute_streak(dates)}

    @staticmethod
    def _compute_streak(dates: set) -> int:
        """Dias consecutivos com >=1 conclusão, terminando em hoje ou ontem (não
        zera no meio do dia — se só ontem tem conclusão, o streak segue ativo)."""
        today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        yesterday = today - timedelta(days=1)
        if today not in dates and yesterday not in dates:
            return 0
        cursor = today if today in dates else yesterday
        streak = 0
        while cursor in dates:
            streak += 1
            cursor -= timedelta(days=1)
        return streak
