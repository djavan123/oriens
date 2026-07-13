# app/services/capture_service.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CaptureInbox
from app.models.project import Project
from app.models.task import Task, EnergyLevel
from app.repositories.capture_repo import CaptureRepository
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

    async def get_inbox(
        self, user_id: int, limit: Optional[int] = None, offset: int = 0
    ) -> list[CaptureInbox]:
        return await self.repo.get_inbox(user_id, limit=limit, offset=offset)

    async def count_inbox(self, user_id: int) -> int:
        return await self.repo.count_inbox(user_id)

    async def get_all(self, user_id: int) -> list[CaptureInbox]:
        return await self.repo.get_all(user_id)

    async def resolve(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        return await self.repo.resolve(capture_id, user_id)

    async def discard_to_trash(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        return await self.repo.discard_to_trash(capture_id, user_id)

    async def get_trash(
        self, user_id: int, limit: Optional[int] = None, offset: int = 0
    ) -> list[CaptureInbox]:
        return await self.repo.get_trash(user_id, limit=limit, offset=offset)

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
        background_tasks=None,
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
        # O título da página é buscado em background (não bloqueia o request);
        # sem BackgroundTasks disponível, busca inline (caminho legado/testes).
        url = extract_url(title) if project_id is None else None
        if url:
            extra["link_url"] = url
            extra["link_checked_at"] = utcnow()
            if background_tasks is None:
                extra["link_title"] = await fetch_link_title(url)
        task = await TaskService(self.db).create(
            user_id=user_id,
            title=title,
            project_id=project_id,
            energy=energy,
            is_quick_win=is_quick_win,
            **extra,
        )
        if url and background_tasks is not None:
            from app.services.link_title_service import fill_link_title
            background_tasks.add_task(fill_link_title, task.id, user_id, url)
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

    async def discard(self, capture_id: int, user_id: int) -> Optional[CaptureInbox]:
        return await self.repo.mark_processed(capture_id, user_id)

    async def hard_delete(self, capture_id: int, user_id: int) -> None:
        await self.repo.hard_delete(capture_id, user_id)
