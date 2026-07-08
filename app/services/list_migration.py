# app/services/list_migration.py
"""Migração única (idempotente) de notas e itens de repositório antigos para Task.

Roda no boot (lifespan do app web) depois de init_db(). Não apaga os registros
originais em `notes`/`repository_items` — cria uma Task equivalente na lista
interna correspondente (Notas/Repositório) se ainda não existir uma.
"""
import logging
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import _MIGRATION_LOCK_KEY
from app.models.note import Note
from app.models.repository import RepositoryItem
from app.models.task import Task, TaskStatus, EnergyLevel
from app.models.user import User
from app.repositories.task_list_repo import TaskListRepository
from app.utils.link_meta import extract_url, fetch_link_title
from app.utils.time import utcnow

logger = logging.getLogger("oriens.list_migration")

_TITLE_MAX = 2000


async def migrate_notes_and_repository_to_tasks(db: AsyncSession) -> None:
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        # Mesma chave do lock de DDL em init_db() (não uma própria): com 3 workers do
        # gunicorn rodando o lifespan em paralelo, um worker pode estar no meio do
        # ALTER TABLE tasks (AccessExclusiveLock) enquanto outro já está fazendo INSERT
        # INTO tasks aqui — reusar a mesma trava serializa migração de schema e de
        # dados entre todos os workers e elimina o deadlock entre as duas transações.
        await db.execute(text(f"SELECT pg_advisory_xact_lock({_MIGRATION_LOCK_KEY})"))

    list_repo = TaskListRepository(db)
    user_ids = (await db.execute(select(User.id))).scalars().all()
    for user_id in user_ids:
        await list_repo.ensure_system_lists(user_id)

    try:
        await _migrate_notes(db, list_repo)
    except Exception:
        logger.exception("Falha ao migrar notas antigas para tasks")
    try:
        await _migrate_repository_items(db, list_repo)
    except Exception:
        logger.exception("Falha ao migrar itens de repositório antigos para tasks")


async def _already_migrated(db: AsyncSession, user_id: int, list_id: int, title: str, created_at) -> bool:
    result = await db.execute(
        select(Task.id).where(
            Task.user_id == user_id,
            Task.list_id == list_id,
            Task.title == title,
            Task.created_at == created_at,
        )
    )
    return result.scalar_one_or_none() is not None


async def _migrate_notes(db: AsyncSession, list_repo: TaskListRepository) -> None:
    notes = (
        await db.execute(select(Note).where(Note.project_id.is_(None)))
    ).scalars().all()
    if not notes:
        return
    list_id_cache: dict[int, int] = {}
    created = False
    for note in notes:
        list_id = list_id_cache.get(note.user_id)
        if list_id is None:
            tl = await list_repo.get_system_list(note.user_id, "notes")
            if tl is None:
                continue
            list_id = tl.id
            list_id_cache[note.user_id] = list_id
        title = (note.content or "").strip()[:_TITLE_MAX]
        if not title:
            continue
        if await _already_migrated(db, note.user_id, list_id, title, note.created_at):
            continue
        db.add(Task(
            user_id=note.user_id,
            list_id=list_id,
            project_id=None,
            title=title,
            status=TaskStatus.pending,
            energy=EnergyLevel.medium,
            created_at=note.created_at,
        ))
        created = True
    if created:
        await db.commit()


async def _migrate_repository_items(db: AsyncSession, list_repo: TaskListRepository) -> None:
    items = (await db.execute(select(RepositoryItem))).scalars().all()
    if not items:
        return

    # 1) Resolve o que falta migrar (só leituras — SELECTs rápidos, sem I/O de rede).
    list_id_cache: dict[int, int] = {}
    pending: list[tuple] = []
    for item in items:
        list_id = list_id_cache.get(item.user_id)
        if list_id is None:
            tl = await list_repo.get_system_list(item.user_id, "repository")
            if tl is None:
                continue
            list_id = tl.id
            list_id_cache[item.user_id] = list_id
        title = (item.content or "").strip()[:_TITLE_MAX]
        if not title:
            continue
        if await _already_migrated(db, item.user_id, list_id, title, item.created_at):
            continue
        pending.append((item, list_id, title, extract_url(title)))

    if not pending:
        return

    # 2) Busca os títulos de link (I/O de rede) ANTES de montar os objetos a inserir —
    # evita manter INSERTs pendentes (e locks) na transação durante chamadas HTTP lentas.
    link_titles: dict[int, Optional[str]] = {}
    for item, _list_id, _title, link_url in pending:
        if link_url:
            link_titles[item.id] = await fetch_link_title(link_url)

    # 3) Só agora monta e grava — sem nenhum SELECT/HTTP entre os adds e o commit.
    for item, list_id, title, link_url in pending:
        db.add(Task(
            user_id=item.user_id,
            list_id=list_id,
            project_id=None,
            title=title,
            status=TaskStatus.pending,
            energy=EnergyLevel.medium,
            created_at=item.created_at,
            link_url=link_url,
            link_title=link_titles.get(item.id) if link_url else None,
            link_checked_at=utcnow() if link_url else None,
        ))
    await db.commit()
