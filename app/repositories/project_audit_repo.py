# app/repositories/project_audit_repo.py
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_audit import ProjectAudit


class ProjectAuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_project(self, project_id: int, limit: int = 50) -> list[ProjectAudit]:
        result = await self.db.execute(
            select(ProjectAudit)
            .where(ProjectAudit.project_id == project_id)
            .order_by(ProjectAudit.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def record(
        self,
        project_id: int,
        user_id: int,
        field: str,
        old_value: Optional[str],
        new_value: Optional[str],
    ) -> None:
        """Adiciona uma entrada de auditoria à sessão (commit fica a cargo de quem chamou)."""
        self.db.add(
            ProjectAudit(
                project_id=project_id,
                user_id=user_id,
                field=field,
                old_value=old_value,
                new_value=new_value,
            )
        )
