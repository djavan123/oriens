# app/repositories/project_milestone_repo.py
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_milestone import ProjectMilestone


class ProjectMilestoneRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_project(self, project_id: int) -> list[ProjectMilestone]:
        result = await self.db.execute(
            select(ProjectMilestone)
            .where(ProjectMilestone.project_id == project_id)
            .order_by(ProjectMilestone.done.asc(), ProjectMilestone.due_date.asc().nulls_last(), ProjectMilestone.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(
        self, project_id: int, user_id: int, title: str, due_date: Optional[datetime] = None
    ) -> ProjectMilestone:
        milestone = ProjectMilestone(
            project_id=project_id, user_id=user_id, title=title, due_date=due_date
        )
        self.db.add(milestone)
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone

    async def get_by_id(self, milestone_id: int, user_id: int) -> Optional[ProjectMilestone]:
        result = await self.db.execute(
            select(ProjectMilestone).where(
                ProjectMilestone.id == milestone_id,
                ProjectMilestone.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def toggle_done(self, milestone_id: int, user_id: int) -> Optional[ProjectMilestone]:
        milestone = await self.get_by_id(milestone_id, user_id)
        if not milestone:
            return None
        milestone.done = not milestone.done
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone

    async def delete(self, milestone_id: int, user_id: int) -> bool:
        milestone = await self.get_by_id(milestone_id, user_id)
        if not milestone:
            return False
        await self.db.delete(milestone)
        await self.db.commit()
        return True
