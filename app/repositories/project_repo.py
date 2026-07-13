# app/repositories/project_repo.py
from datetime import datetime
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus
from app.models.project_timeline import ProjectTimeline


class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_by_user(
        self,
        user_id: int,
        context_id: Optional[int] = None,
        archived_only: bool = False,
        include_archived: bool = False,
        limit: int = 200,
    ) -> list[Project]:
        # `limit=200` é guard-rail (projetos são dezenas; protege contra anomalia).
        q = (
            select(Project)
            .where(Project.user_id == user_id, Project.status != ProjectStatus.concluido)
        )
        if archived_only:
            q = q.where(Project.archived.is_(True))
        elif not include_archived:
            q = q.where(Project.archived.is_(False))
        if context_id is not None:
            q = q.where(
                (Project.context_id.is_(None)) | (Project.context_id == context_id)
            )
        result = await self.db.execute(
            q.order_by(Project.priority.asc(), Project.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_active_by_user(
        self, user_id: int, context_id: Optional[int] = None, limit: int = 200
    ) -> list[Project]:
        q = (
            select(Project)
            .where(
                Project.user_id == user_id,
                Project.status == ProjectStatus.em_andamento,
                Project.archived.is_(False),
            )
        )
        # Contexto antes de prioridade: projeto sem contexto aparece em todos.
        if context_id is not None:
            q = q.where(
                (Project.context_id.is_(None)) | (Project.context_id == context_id)
            )
        result = await self.db.execute(
            q.order_by(Project.priority.asc(), Project.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, project_id: int, user_id: int) -> Optional[Project]:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def count_active(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Project)
            .where(
                Project.user_id == user_id,
                Project.status == ProjectStatus.em_andamento,
                Project.archived.is_(False),
            )
        )
        return result.scalar_one()

    async def get_last_activity(self, project_id: int) -> Optional[datetime]:
        """Returns the most recent activity datetime from project_timeline."""
        from app.repositories.project_timeline_repo import ProjectTimelineRepository
        timeline_dt = await ProjectTimelineRepository(self.db).get_last_activity(project_id)
        if timeline_dt is not None:
            return timeline_dt
        # Fallback: use project's own updated_at for projects with no timeline entries.
        project = await self.get_by_id_unsafe(project_id)
        return project.updated_at if project else None

    async def get_by_id_unsafe(self, project_id: int) -> Optional[Project]:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def create(self, user_id: int, **kwargs) -> Project:
        project = Project(user_id=user_id, **kwargs)
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update(self, project: Project, **kwargs) -> Project:
        for key, value in kwargs.items():
            setattr(project, key, value)
        await self.db.commit()
        await self.db.refresh(project)
        return project
