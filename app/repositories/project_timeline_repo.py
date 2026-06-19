# app/repositories/project_timeline_repo.py
from datetime import datetime
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_timeline import ProjectTimeline, TimelineEventType


class ProjectTimelineRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_project(self, project_id: int, limit: int = 50) -> list[ProjectTimeline]:
        result = await self.db.execute(
            select(ProjectTimeline)
            .where(ProjectTimeline.project_id == project_id)
            .order_by(ProjectTimeline.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def record(
        self,
        project_id: int,
        user_id: int,
        event_type: TimelineEventType,
        description: Optional[str] = None,
    ) -> None:
        self.db.add(ProjectTimeline(
            project_id=project_id,
            user_id=user_id,
            event_type=event_type.value,
            description=description,
        ))

    async def get_last_activity(self, project_id: int) -> Optional[datetime]:
        result = await self.db.execute(
            select(func.max(ProjectTimeline.created_at))
            .where(ProjectTimeline.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def last_activity_by_projects(
        self, project_ids: list[int]
    ) -> dict[int, datetime]:
        """{project_id: data da atividade mais recente}, em uma query."""
        if not project_ids:
            return {}
        result = await self.db.execute(
            select(ProjectTimeline.project_id, func.max(ProjectTimeline.created_at))
            .where(ProjectTimeline.project_id.in_(project_ids))
            .group_by(ProjectTimeline.project_id)
        )
        return {row[0]: row[1] for row in result.all()}
