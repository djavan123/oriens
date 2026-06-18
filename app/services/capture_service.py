# app/services/capture_service.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CaptureInbox
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task, EnergyLevel
from app.repositories.capture_repo import CaptureRepository
from app.repositories.note_repo import NoteRepository
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


class CaptureService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CaptureRepository(db)

    async def create(self, user_id: int, content: str) -> CaptureInbox:
        return await self.repo.create(user_id=user_id, content=content.strip())

    async def get_inbox(self, user_id: int) -> list[CaptureInbox]:
        return await self.repo.get_unprocessed(user_id)

    async def get_all(self, user_id: int) -> list[CaptureInbox]:
        return await self.repo.get_all(user_id)

    async def process_as_task(
        self,
        capture_id: int,
        user_id: int,
        title: str,
        project_id: Optional[int] = None,
        energy: EnergyLevel = EnergyLevel.medium,
        is_quick_win: bool = False,
        context_id: Optional[int] = None,
    ) -> tuple[CaptureInbox, Task]:
        extra = {"context_id": context_id} if context_id is not None else {}
        task = await TaskService(self.db).create(
            user_id=user_id,
            title=title,
            project_id=project_id,
            energy=energy,
            is_quick_win=is_quick_win,
            **extra,
        )
        capture = await self.repo.mark_processed(capture_id, user_id)
        return capture, task

    async def process_as_project(
        self,
        capture_id: int,
        user_id: int,
        name: str,
        objective: Optional[str] = None,
        priority: int = 2,
    ) -> tuple[CaptureInbox, Project]:
        project = await ProjectService(self.db).create(
            user_id=user_id,
            name=name,
            objective=objective,
            priority=priority,
        )
        capture = await self.repo.mark_processed(capture_id, user_id)
        return capture, project

    async def process_as_note(
        self,
        capture_id: int,
        user_id: int,
        content: str,
        project_id: Optional[int] = None,
    ) -> tuple[CaptureInbox, Note]:
        note = await NoteRepository(self.db).create(
            user_id=user_id,
            content=content,
            project_id=project_id,
        )
        capture = await self.repo.mark_processed(capture_id, user_id)
        return capture, note

    async def discard(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        return await self.repo.mark_processed(capture_id, user_id)
