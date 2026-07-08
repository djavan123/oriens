from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus
from app.models.project_timeline import TimelineEventType
from app.repositories.project_repo import ProjectRepository
from app.repositories.project_audit_repo import ProjectAuditRepository
from app.repositories.project_timeline_repo import ProjectTimelineRepository

_CLOSING_STATUSES = {ProjectStatus.concluido}

# Dias sem atividade para um projeto em andamento ser considerado "parado".
_STALLED_DAYS = 7


def _days_since(dt: Optional[datetime]) -> Optional[int]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return (datetime.utcnow() - dt).days

# Campos cujas alterações são registradas no histórico do projeto.
_AUDITED_FIELDS = ("status", "priority", "name", "deadline", "objective", "scope", "notes", "proxima_acao")


def _audit_str(value) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "value"):  # Enum
        return str(value.value)
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    text = str(value)
    return text if len(text) <= 255 else text[:252] + "..."


_STATUS_LABELS = {
    "em_andamento": "Em andamento",
    "nao_iniciado": "Não iniciado",
    "concluido": "Concluído",
}


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectRepository(db)
        self.audit = ProjectAuditRepository(db)
        self.timeline = ProjectTimelineRepository(db)

    async def get_all(
        self,
        user_id: int,
        context_id: Optional[int] = None,
        archived_only: bool = False,
        include_archived: bool = False,
    ) -> list[Project]:
        return await self.repo.get_all_by_user(
            user_id,
            context_id=context_id,
            archived_only=archived_only,
            include_archived=include_archived,
        )

    async def get_by_id(self, project_id: int, user_id: int) -> Optional[Project]:
        return await self.repo.get_by_id(project_id, user_id)

    async def create(
        self,
        user_id: int,
        name: str,
        objective: Optional[str] = None,
        scope: Optional[str] = None,
        priority: int = 2,
        status: ProjectStatus = ProjectStatus.nao_iniciado,
        notes: Optional[str] = None,
        deadline: Optional[datetime] = None,
        context_id: Optional[int] = None,
        responsavel_id: Optional[int] = None,
        proxima_acao: Optional[str] = None,
    ) -> Project:
        if priority not in (0, 1, 2, 3):
            priority = 2
        project = await self.repo.create(
            user_id=user_id,
            name=name,
            objective=objective,
            scope=scope,
            priority=priority,
            status=status,
            notes=notes,
            deadline=deadline,
            context_id=context_id,
            responsavel_id=responsavel_id,
            proxima_acao=proxima_acao,
        )
        self.timeline.record(project.id, user_id, TimelineEventType.project_created, f'Projeto "{project.name}" criado')
        await self.db.commit()
        return project

    async def get_project_next_action(self, project_id: int, user_id: int) -> dict:
        """Próxima ação executável do projeto.

        Retorna dict com:
          task       — primeira tarefa pendente em ordem (seção → order_index) ou None
          executable — True somente se há tarefa pendente
        """
        from app.repositories.task_repo import TaskRepository
        task = await TaskRepository(self.db).get_project_next_task(project_id, user_id)
        return {
            "task": task,
            "proxima_acao": None,
            "executable": task is not None,
        }

    async def get_executability(self, user_id: int, projects: list[Project]) -> dict:
        """Mapa {project_id: estado operacional} para a listagem de projetos.

        Estados: completed | not_started | no_action | stalled | executable.
        next_task = primeira tarefa pendente em ordem manual; next_text = fallback
        proxima_acao quando não há tarefa pendente.
        """
        ids = [p.id for p in projects]
        if not ids:
            return {}
        from app.repositories.task_repo import TaskRepository
        trepo = TaskRepository(self.db)
        next_tasks = await trepo.next_pending_tasks_by_project(user_id, ids)
        counts = await trepo.pending_count_by_project(user_id, ids)
        activity = await self.timeline.last_activity_by_projects(ids)

        out: dict[int, dict] = {}
        for p in projects:
            nt = next_tasks.get(p.id)
            executable = nt is not None
            last = activity.get(p.id) or p.updated_at

            if p.status == ProjectStatus.concluido:
                state = "completed"
            elif p.status == ProjectStatus.nao_iniciado:
                state = "not_started"
            elif not executable:
                state = "no_action"
            else:
                days = _days_since(last)
                state = "stalled" if (days is not None and days >= _STALLED_DAYS) else "executable"

            out[p.id] = {
                "state": state,
                "next_task": nt,
                "next_text": None,
                "pending_count": counts.get(p.id, 0),
                "last_activity": last,
                "executable": executable,
            }
        return out

    async def update(self, project_id: int, user_id: int, **kwargs) -> Optional[Project]:
        project = await self.repo.get_by_id(project_id, user_id)
        if not project:
            return None
        if "priority" in kwargs and kwargs["priority"] not in (0, 1, 2, 3):
            kwargs.pop("priority")
        new_status = kwargs.get("status")
        if new_status is not None and new_status != project.status:
            if new_status == ProjectStatus.concluido and project.status != ProjectStatus.concluido:
                kwargs["done_at"] = datetime.utcnow()
            elif new_status != ProjectStatus.concluido and project.status == ProjectStatus.concluido:
                kwargs["done_at"] = None
        # Registra no histórico cada campo auditado que realmente mudou.
        for field in _AUDITED_FIELDS:
            if field in kwargs:
                old = getattr(project, field)
                new = kwargs[field]
                if old != new:
                    self.audit.record(
                        project_id, user_id, field, _audit_str(old), _audit_str(new)
                    )

        # Registra mudança de status na timeline.
        if new_status is not None and new_status != project.status:
            label = _STATUS_LABELS.get(new_status.value, new_status.value)
            self.timeline.record(
                project_id, user_id, TimelineEventType.status_changed,
                f"Status alterado para {label}"
            )

        return await self.repo.update(project, **kwargs)
