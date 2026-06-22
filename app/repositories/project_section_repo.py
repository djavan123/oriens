# app/repositories/project_section_repo.py
from typing import Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_section import ProjectSection
from app.models.task import Task


class ProjectSectionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_by_project(self, project_id: int) -> list[ProjectSection]:
        result = await self.db.execute(
            select(ProjectSection)
            .where(ProjectSection.project_id == project_id)
            .order_by(ProjectSection.order_index.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, section_id: int, project_id: int) -> Optional[ProjectSection]:
        result = await self.db.execute(
            select(ProjectSection).where(
                ProjectSection.id == section_id,
                ProjectSection.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, project_id: int, name: str) -> ProjectSection:
        result = await self.db.execute(
            select(func.max(ProjectSection.order_index)).where(
                ProjectSection.project_id == project_id
            )
        )
        max_idx = result.scalar_one_or_none()
        next_idx = (max_idx + 1) if max_idx is not None else 0
        section = ProjectSection(project_id=project_id, name=name, order_index=next_idx)
        self.db.add(section)
        await self.db.commit()
        await self.db.refresh(section)
        return section

    async def update(self, section: ProjectSection, **kwargs) -> ProjectSection:
        for key, value in kwargs.items():
            setattr(section, key, value)
        await self.db.commit()
        await self.db.refresh(section)
        return section

    async def delete_with_nullify(self, section_id: int, project_id: int) -> bool:
        """Nullifica section_id nas tarefas e apaga a seção. Retorna False se não encontrada."""
        section = await self.get_by_id(section_id, project_id)
        if not section:
            return False
        await self.db.execute(
            update(Task).where(Task.section_id == section_id).values(section_id=None)
        )
        await self.db.delete(section)
        await self.db.commit()
        return True
