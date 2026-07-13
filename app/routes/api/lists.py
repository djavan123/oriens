# app/routes/api/lists.py
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.task_list_repo import TaskListRepository
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api", tags=["api:lists"])


# --- Listas personalizadas (SCRIPT Listas) --------------------------------

@router.post("/lists", response_class=HTMLResponse)
async def create_list(
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_list = await TaskListRepository(db).create(current_user.id, name)
    if task_list is None:
        return HTMLResponse(
            '<p class="text-oriens-alert text-xs">Nome não pode ser vazio.</p>',
            headers={"HX-Retarget": "#new-list-error", "HX-Reswap": "innerHTML"},
        )
    # Recarrega /lists já com a nova lista selecionada (solução mais simples).
    return HTMLResponse("", headers={"HX-Redirect": f"/lists?list={task_list.id}"})


@router.patch("/lists/{list_id}", response_class=HTMLResponse)
async def rename_list(
    list_id: int,
    request: Request,
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_list = await TaskListRepository(db).update_name(list_id, current_user.id, name)
    if task_list is None:
        # Nome vazio, lista inexistente ou lista interna (não renomeável nesta fase).
        raise HTTPException(status_code=400)
    return HTMLResponse("", headers={"HX-Redirect": f"/lists?list={task_list.id}"})


@router.delete("/lists/{list_id}", response_class=HTMLResponse)
async def archive_list(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = await TaskListRepository(db).archive(list_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404)
    # Tarefas voltaram para "Tarefas avulsas"; recarrega mostrando essa lista.
    return HTMLResponse("", headers={"HX-Redirect": "/lists"})


# Endpoints legados POST/DELETE /api/repository removidos: a UI não os usava
# desde o script "Listas unificadas" (repositório é só uma lista de Tasks).
