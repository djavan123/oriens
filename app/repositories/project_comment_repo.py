# app/repositories/project_comment_repo.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_comment import ProjectComment


class ProjectCommentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_project(self, project_id: int) -> list[ProjectComment]:
        result = await self.db.execute(
            select(ProjectComment)
            .where(ProjectComment.project_id == project_id)
            .order_by(ProjectComment.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(self, project_id: int, user_id: int, content: str) -> ProjectComment:
        comment = ProjectComment(project_id=project_id, user_id=user_id, content=content)
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def delete(self, comment_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(ProjectComment).where(
                ProjectComment.id == comment_id,
                ProjectComment.user_id == user_id,
            )
        )
        comment = result.scalar_one_or_none()
        if not comment:
            return False
        await self.db.delete(comment)
        await self.db.commit()
        return True
