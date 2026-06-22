# app/routes/lists.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.task_repo import TaskRepository
from app.repositories.note_repo import NoteRepository
from app.repositories.repository_repo import RepositoryRepository
from app.utils.auth import get_current_user
from app.utils.context_utils import resolve_active_context

router = APIRouter(tags=["lists"])


@router.get("/lists", response_class=HTMLResponse)
async def lists_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = await TaskRepository(db).get_standalone_tasks(current_user.id)
    notes = await NoteRepository(db).get_standalone(current_user.id)
    repo_items = await RepositoryRepository(db).get_all_by_user(current_user.id)

    _, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )

    return templates.TemplateResponse(
        request,
        "lists.html",
        {
            "user": current_user,
            "tasks": tasks,
            "notes": notes,
            "repo_items": repo_items,
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
        },
    )
