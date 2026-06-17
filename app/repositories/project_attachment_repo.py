# app/repositories/project_attachment_repo.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_attachment import ProjectAttachment


class ProjectAttachmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_project(self, project_id: int) -> list[ProjectAttachment]:
        result = await self.db.execute(
            select(ProjectAttachment)
            .where(ProjectAttachment.project_id == project_id)
            .order_by(ProjectAttachment.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, attachment_id: int, user_id: int):
        result = await self.db.execute(
            select(ProjectAttachment).where(
                ProjectAttachment.id == attachment_id,
                ProjectAttachment.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, project_id: int, user_id: int, filename: str, original_name: str, size: int) -> ProjectAttachment:
        att = ProjectAttachment(
            project_id=project_id,
            user_id=user_id,
            filename=filename,
            original_name=original_name,
            size=size,
        )
        self.db.add(att)
        await self.db.commit()
        await self.db.refresh(att)
        return att

    async def delete(self, attachment_id: int, user_id: int):
        result = await self.db.execute(
            select(ProjectAttachment).where(
                ProjectAttachment.id == attachment_id,
                ProjectAttachment.user_id == user_id,
            )
        )
        att = result.scalar_one_or_none()
        if not att:
            return None
        await self.db.delete(att)
        await self.db.commit()
        return att
