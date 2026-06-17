# app/routes/api/tasks.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import EnergyLevel
from app.models.user import User
from app.services.task_service import TaskService, TaskVerbError
from app.utils.auth import get_current_user


def _parse_date(v: Optional[str]) -> Optional[datetime]:
    if not v or not v.strip():
        return None
    try:
        return datetime.strptime(v.strip(), "%Y-%m-%d")
    except ValueError:
        return None


def _parse_int(v: Optional[str]) -> Optional[int]:
    if not v or not v.strip():
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _parse_remind(date_str: Optional[str], time_str: Optional[str]) -> Optional[datetime]:
    """Combina Data + Hora num datetime. Sem data → None. Sem hora → 09:00."""
    if not date_str or not date_str.strip():
        return None
    t = (time_str or "").strip() or "09:00"
    try:
        return datetime.strptime(f"{date_str.strip()} {t}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None

router = APIRouter(prefix="/api/tasks", tags=["api:tasks"])


def _verb_error_response(exc: TaskVerbError) -> HTMLResponse:
    suggestions_html = "".join(
        f'<button type="button" '
        f'onclick="this.closest(\'form\').querySelector(\'[name=title]\').value=\'{s}\';'
        f'this.closest(\'form\').querySelector(\'[name=title]\').focus()" '
        f'class="block text-oriens-accent text-xs hover:opacity-80 transition-opacity text-left">'
        f'{s}</button>'
        for s in exc.suggestions
    )
    html = (
        f'<p class="text-oriens-alert text-sm">{exc}</p>'
        f'<div class="mt-2 space-y-1">'
        f'<p class="text-oriens-secondary text-xs">Sugestões:</p>'
        f'{suggestions_html}'
        f'</div>'
    )
    return HTMLResponse(
        html,
        headers={"HX-Retarget": "#task-form-error", "HX-Reswap": "innerHTML"},
    )


@router.post("", response_class=HTMLResponse)
async def create_task(
    request: Request,
    title: str = Form(...),
    project_id: Optional[str] = Form(None),
    parent_id: Optional[str] = Form(None),
    energy: EnergyLevel = Form(EnergyLevel.medium),
    is_quick_win: bool = Form(False),
    context_id: Optional[str] = Form(None),
    cognitive_load: Optional[str] = Form(None),
    deadline: Optional[str] = Form(None),
    responsavel_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.task import CognitiveLoad
    title = title.strip()
    if not title:
        return HTMLResponse(
            '<p class="text-oriens-alert text-sm">Título é obrigatório.</p>',
            headers={"HX-Retarget": "#task-form-error", "HX-Reswap": "innerHTML"},
        )
    extra = {}
    proj_id = _parse_int(project_id)
    # Herança de contexto: tarefa dentro de um projeto herda o contexto dele.
    if proj_id is not None:
        from app.services.project_service import ProjectService
        project = await ProjectService(db).get_by_id(proj_id, current_user.id)
        if project is not None:
            extra["context_id"] = project.context_id
    else:
        cid = _parse_int(context_id)
        if cid is not None:
            extra["context_id"] = cid
    pid = _parse_int(parent_id)
    if pid is not None:
        extra["parent_id"] = pid
    if cognitive_load and cognitive_load in {c.value for c in CognitiveLoad}:
        extra["cognitive_load"] = CognitiveLoad(cognitive_load)
    dl = _parse_date(deadline)
    if dl is not None:
        extra["deadline"] = dl
    rid = _parse_int(responsavel_id)
    if rid is not None:
        extra["responsavel_id"] = rid
    if tags is not None:
        extra["tags"] = tags.strip() or None
    service = TaskService(db)
    try:
        task = await service.create(
            user_id=current_user.id,
            title=title,
            project_id=proj_id,
            energy=energy,
            is_quick_win=is_quick_win,
            **extra,
        )
    except TaskVerbError as e:
        return _verb_error_response(e)
    return templates.TemplateResponse(
        request, "partials/task_item.html", {"task": task}
    )


@router.patch("/{task_id}/done", response_class=HTMLResponse)
async def mark_done(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.mark_done(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/task_item.html", {"task": task}
    )


@router.patch("/{task_id}/blocked", response_class=HTMLResponse)
async def mark_blocked(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.mark_blocked(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/task_item.html", {"task": task}
    )


@router.patch("/{task_id}/pending", response_class=HTMLResponse)
async def mark_pending(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.mark_pending(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/task_item.html", {"task": task}
    )


@router.patch("/{task_id}/archive", response_class=HTMLResponse)
async def archive_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.archive(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)
    return HTMLResponse("")


@router.get("/{task_id}/cancel-edit", response_class=HTMLResponse)
async def cancel_edit(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.get_by_id(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/task_item.html", {"task": task}
    )


@router.get("/{task_id}/edit", response_class=HTMLResponse)
async def edit_form(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.repositories.context_repo import ContextRepository
    from app.repositories.label_repo import LabelRepository
    service = TaskService(db)
    task = await service.get_by_id(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)
    contexts = await ContextRepository(db).get_all_by_user(current_user.id)
    context_labels = {c.id: c.name for c in contexts}
    user_labels = await LabelRepository(db).get_all_by_user(current_user.id)
    from sqlalchemy import select
    from app.models.user import User as UserModel
    users_result = await db.execute(select(UserModel).order_by(UserModel.name))
    users = list(users_result.scalars().all())
    return templates.TemplateResponse(
        request,
        "partials/task_edit_form.html",
        {"task": task, "contexts": contexts, "context_labels": context_labels,
         "user_labels": user_labels, "users": users},
    )


@router.patch("/{task_id}", response_class=HTMLResponse)
async def update_task(
    task_id: int,
    request: Request,
    title: str = Form(...),
    energy: Optional[str] = Form(None),
    is_quick_win: bool = Form(False),
    deadline: Optional[str] = Form(None),
    responsavel_id: Optional[str] = Form(None),
    context_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    remind_date: Optional[str] = Form(None),
    remind_time: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = title.strip()
    if not title:
        return HTMLResponse(
            '<p class="text-oriens-alert text-xs">Título é obrigatório.</p>',
            headers={"HX-Retarget": f"#task-edit-error-{task_id}", "HX-Reswap": "innerHTML"},
        )
    service = TaskService(db)
    existing = await service.get_by_id(task_id, current_user.id)
    if not existing:
        raise HTTPException(status_code=404)

    kwargs: dict = {"title": title, "is_quick_win": is_quick_win, "deadline": _parse_date(deadline)}
    if energy and energy in {e.value for e in EnergyLevel}:
        kwargs["energy"] = EnergyLevel(energy)
    rid = _parse_int(responsavel_id)
    if rid is not None:
        kwargs["responsavel_id"] = rid
    # Contexto: tarefa de projeto herda do projeto (travado) → ignora o que vier.
    if existing.project_id is None and context_id is not None:
        kwargs["context_id"] = _parse_int(context_id)
    if tags is not None:
        kwargs["tags"] = tags.strip() or None
    # Lembrete: ao mudar, reseta os flags para poder disparar de novo.
    new_remind = _parse_remind(remind_date, remind_time)
    if new_remind != existing.remind_at:
        kwargs["remind_at"] = new_remind
        kwargs["reminder_telegram_sent"] = False
        kwargs["reminder_acked"] = False

    try:
        task = await service.update(task_id, current_user.id, **kwargs)
    except TaskVerbError as e:
        return _verb_error_response(e)
    if not task:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/task_item.html", {"task": task}
    )
