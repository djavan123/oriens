# app/routes/api/ai.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.repositories.task_repo import TaskRepository
from app.services.ai_service import get_ai_provider
from app.services.dashboard_service import DashboardService
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/ai", tags=["api:ai"])


def _ai_disabled_response() -> HTMLResponse:
    return HTMLResponse(
        '<p class="text-oriens-secondary text-xs italic">IA não está habilitada.</p>'
    )


def _ai_empty_response() -> HTMLResponse:
    return HTMLResponse(
        '<p class="text-oriens-secondary text-xs italic">Sem sugestões disponíveis.</p>'
    )


@router.post("/break-task/{task_id}", response_class=HTMLResponse)
async def break_task(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not get_settings().AI_ENABLED:
        return _ai_disabled_response()

    task = await TaskRepository(db).get_by_id(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)

    provider = get_ai_provider()
    items = await provider.break_task(task.title)

    if not items:
        return _ai_empty_response()
    return templates.TemplateResponse(
        request,
        "partials/ai_result.html",
        {"label": "Subtarefas sugeridas", "items": items},
    )


@router.post("/suggest-actions/{project_id}", response_class=HTMLResponse)
async def suggest_actions(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not get_settings().AI_ENABLED:
        return _ai_disabled_response()

    project = await ProjectRepository(db).get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404)

    provider = get_ai_provider()
    items = await provider.suggest_next_actions(project)

    if not items:
        return _ai_empty_response()
    return templates.TemplateResponse(
        request,
        "partials/ai_result.html",
        {"label": "Próximas ações sugeridas", "items": items},
    )


@router.post("/overload-context", response_class=HTMLResponse)
async def overload_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not get_settings().AI_ENABLED:
        return _ai_disabled_response()

    service = DashboardService(db)
    data = await service.get_dashboard_data(current_user.id)

    user_data = {
        "active_projects": data.overload.active_projects_count,
        "pending_tasks": data.overload.pending_tasks_count,
        "overload_score": data.overload.score,
    }

    provider = get_ai_provider()
    text = await provider.detect_overload_context(user_data)

    if not text:
        return _ai_empty_response()
    return HTMLResponse(
        f'<p class="text-oriens-secondary text-sm italic leading-relaxed">{text}</p>'
    )
