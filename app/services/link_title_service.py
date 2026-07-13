# app/services/link_title_service.py
"""Busca o título de um link EM SEGUNDO PLANO (FastAPI BackgroundTasks).

`fetch_link_title` leva até ~5s de I/O externo — rodá-lo dentro do request
handler segura um worker web inteiro por requisição. O fluxo passou a ser:
o request grava `link_url` na hora (síncrono, barato) e agenda esta função,
que busca o título e o grava numa sessão própria depois da resposta.
"""
import logging

from app.utils.link_meta import fetch_link_title
from app.utils.time import utcnow

logger = logging.getLogger("oriens.link_title")


async def fill_link_title(task_id: int, user_id: int, url: str) -> None:
    """Nunca levanta (roda desanexado do request)."""
    try:
        title = await fetch_link_title(url)
        if not title:
            return
        from app.database import AsyncSessionLocal
        from app.repositories.task_repo import TaskRepository

        async with AsyncSessionLocal() as db:
            repo = TaskRepository(db)
            task = await repo.get_by_id(task_id, user_id)
            # Só grava se o link ainda for o mesmo (o usuário pode ter editado no meio).
            if task and task.link_url == url:
                task.link_title = title
                task.link_checked_at = utcnow()
                await db.commit()
    except Exception:
        logger.exception("Falha ao preencher título do link em background")
