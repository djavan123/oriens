# app/routes/lists.py
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.task_repo import TaskRepository
from app.repositories.task_list_repo import TaskListRepository
from app.utils.auth import get_current_user
from app.utils.context_utils import resolve_active_context

router = APIRouter(tags=["lists"])


@router.get("/lists", response_class=HTMLResponse)
async def lists_page(
    request: Request,
    list: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    context_id, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )

    list_repo = TaskListRepository(db)
    task_repo = TaskRepository(db)

    # Garante Notas/Repositório (idempotente; cobre usuários criados após o boot).
    await list_repo.ensure_system_lists(current_user.id)
    all_lists = await list_repo.get_active_by_user(current_user.id)
    notes_list = next((l for l in all_lists if l.system_key == "notes"), None)
    repo_list = next((l for l in all_lists if l.system_key == "repository"), None)
    custom_lists = [l for l in all_lists if l.system_key is None]

    # Resolve a lista ativa a partir do ?list=. Ausente/"tasks"/inválido → padrão (avulsas).
    active_list = None
    active_list_id: Optional[int] = None
    if list and list not in ("tasks", "default", "null"):
        try:
            wanted = int(list)
        except ValueError:
            wanted = None
        if wanted is not None:
            active_list = next((l for l in all_lists if l.id == wanted), None)
            active_list_id = active_list.id if active_list else None

    # A lista é apenas agrupamento: título/placeholder derivam só do nome da lista.
    if active_list is None:
        title = "Tarefas avulsas"
    else:
        title = active_list.name
    placeholder = f'Nova tarefa em "{title}"'

    # Tarefas da lista ativa. O contexto ativo filtra TODAS as listas igualmente
    # (uma task numa lista funciona exatamente como uma tarefa avulsa).
    tasks = await task_repo.get_standalone_by_list(
        current_user.id, active_list_id, context_id=context_id,
    )

    count_default = await task_repo.count_standalone_default(current_user.id)
    counts_by_list = await task_repo.count_by_list(current_user.id)

    return templates.TemplateResponse(
        request,
        "lists.html",
        {
            "user": current_user,
            "tasks": tasks,
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
            "active_context_id": context_id,
            # Listas
            "custom_lists": custom_lists,
            "notes_list": notes_list,
            "repo_list": repo_list,
            "count_default": count_default,
            "counts_by_list": counts_by_list,
            # Lista ativa
            "active_list": active_list,
            "active_list_id": active_list_id,
            "active_title": title,
            "active_placeholder": placeholder,
        },
    )
