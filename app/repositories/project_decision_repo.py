# app/repositories/project_decision_repo.py
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_decision import ProjectDecision


class ProjectDecisionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_project(self, project_id: int) -> list[ProjectDecision]:
        result = await self.db.execute(
            select(ProjectDecision)
            .where(ProjectDecision.project_id == project_id)
            .order_by(ProjectDecision.created_at.desc(), ProjectDecision.id.desc())
        )
        return list(result.scalars().all())

    async def create(self, project_id: int, user_id: int, content: str) -> ProjectDecision:
        decision = ProjectDecision(project_id=project_id, user_id=user_id, content=content)
        self.db.add(decision)
        await self.db.commit()
        await self.db.refresh(decision)
        return decision

    async def get_by_id(self, decision_id: int, user_id: int) -> Optional[ProjectDecision]:
        result = await self.db.execute(
            select(ProjectDecision).where(
                ProjectDecision.id == decision_id,
                ProjectDecision.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, decision_id: int, user_id: int) -> bool:
        decision = await self.get_by_id(decision_id, user_id)
        if not decision:
            return False
        await self.db.delete(decision)
        await self.db.commit()
        return True
