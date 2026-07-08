# app/services/capture_service.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CaptureInbox
from app.models.project import Project
from app.models.task import Task, EnergyLevel
from app.repositories.capture_repo import CaptureRepository
from app.repositories.task_list_repo import TaskListRepository
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.utils.link_meta import extract_url, fetch_link_title
from app.utils.time import utcnow


class CaptureService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CaptureRepository(db)

    async def create(self, user_id: int, content: str) -> CaptureInbox:
        return await self.repo.create(user_id=user_id, content=content.strip())

    async def get_inbox(self, user_id: int) -> list[CaptureInbox]:
        return await self.repo.get_inbox(user_id)

    async def get_all(self, user_id: int) -> list[CaptureInbox]:
        return await self.repo.get_all(user_id)

    async def resolve(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        return await self.repo.resolve(capture_id, user_id)

    async def discard_to_trash(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        return await self.repo.discard_to_trash(capture_id, user_id)

    async def get_trash(self, user_id: int) -> list[CaptureInbox]:
        return await self.repo.get_trash(user_id)

    async def restore(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        return await self.repo.restore(capture_id, user_id)

    async def cleanup_trash(self, user_id: int) -> None:
        await self.repo.cleanup_old_discarded(user_id)

    async def process_as_task(
        self,
        capture_id: int,
        user_id: int,
        title: str,
        project_id: Optional[int] = None,
        energy: EnergyLevel = EnergyLevel.medium,
        is_quick_win: bool = False,
        context_id: Optional[int] = None,
        importancia: Optional[float] = None,
        list_id: Optional[int] = None,
    ) -> tuple[CaptureInbox, Task]:
        extra: dict = {}
        if context_id is not None:
            extra["context_id"] = context_id
        # Importância vinda de Alta/Média/Baixa (SCRIPT 13). None = tarefa de projeto (sem nota).
        if importancia is not None:
            extra["importancia"] = importancia
            extra["sem_nota"] = False
        # list_id só vale para tarefa avulsa de topo (a lista é só agrupamento).
        if list_id is not None:
            extra["list_id"] = list_id
        # Link é global à Task: qualquer conteúdo avulso com URL vira link.
        if project_id is None:
            url = extract_url(title)
            if url:
                extra["link_url"] = url
                extra["link_title"] = await fetch_link_title(url)
                extra["link_checked_at"] = utcnow()
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
        context_id: Optional[int] = None,
        proxima_acao: Optional[str] = None,
    ) -> tuple[CaptureInbox, Project]:
        project = await ProjectService(self.db).create(
            user_id=user_id,
            name=name,
            objective=objective,
            priority=priority,
            context_id=context_id,
            proxima_acao=proxima_acao,
        )
        capture = await self.repo.mark_processed(capture_id, user_id)
        return capture, project

    async def process_as_note(
        self,
        capture_id: int,
        user_id: int,
        content: str,
        project_id: Optional[int] = None,
    ) -> tuple[CaptureInbox, Task]:
        # Nota é apenas uma Task na lista interna "Notas" (tudo é Task).
        lid = await self._system_list_id(user_id, "notes")
        return await self.process_as_task(capture_id, user_id, content, list_id=lid)

    async def discard(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        return await self.repo.mark_processed(capture_id, user_id)

    async def hard_delete(self, capture_id: int, user_id: int) -> None:
        await self.repo.hard_delete(capture_id, user_id)

    async def process_as_repository(
        self,
        capture_id: int,
        user_id: int,
        content: str,
    ) -> tuple[CaptureInbox, Task]:
        # Repositório é apenas uma Task na lista interna "Repositório".
        lid = await self._system_list_id(user_id, "repository")
        return await self.process_as_task(capture_id, user_id, content, list_id=lid)

    async def _system_list_id(self, user_id: int, system_key: str) -> Optional[int]:
        list_repo = TaskListRepository(self.db)
        await list_repo.ensure_system_lists(user_id)
        task_list = await list_repo.get_system_list(user_id, system_key)
        return task_list.id if task_list else None
