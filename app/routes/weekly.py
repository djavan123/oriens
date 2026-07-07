# app/routes/weekly.py
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import ProjectStatus
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.repositories.task_repo import TaskRepository
from app.services.weekly_directive_service import WeeklyDirectiveService, current_week_start
from app.utils.auth import get_current_user
from app.utils.context_utils import resolve_active_context
from app.utils.time import utcnow

router = APIRouter(prefix="/weekly", tags=["weekly"])


@router.get("", response_class=HTMLResponse)
async def weekly_view(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WeeklyDirectiveService(db)
    directive = await service.get_current(current_user.id)

    project_repo = ProjectRepository(db)
    task_repo = TaskRepository(db)
    all_projects = await project_repo.get_all_by_user(current_user.id)
    em_andamento = [p for p in all_projects if p.status == ProjectStatus.em_andamento]

    now_naive = utcnow()

    ids = [p.id for p in em_andamento]
    pending_counts = await task_repo.pending_count_by_project(current_user.id, ids)
    sem_proxima = [p for p in em_andamento if pending_counts.get(p.id, 0) == 0]

    projetos_sem_proxima_acao = []
    for p in sem_proxima:
        last = await project_repo.get_last_activity(p.id)
        ref = last or p.updated_at or p.created_at
        ref_naive = ref.replace(tzinfo=None) if hasattr(ref, 'tzinfo') else ref
        dias = (now_naive - ref_naive).days
        projetos_sem_proxima_acao.append({"project": p, "dias": dias})

    projetos_sem_proxima_acao.sort(key=lambda x: x["dias"], reverse=True)

    _, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )

    week_start = current_week_start()
    return templates.TemplateResponse(
        request,
        "weekly.html",
        {
            "user": current_user,
            "directive": directive,
            "week_start": week_start,
            "projetos_sem_proxima_acao": projetos_sem_proxima_acao,
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
        },
    )


@router.post("", response_class=RedirectResponse)
async def weekly_save(
    request: Request,
    weekly_theme: Optional[str] = Form(None),
    top_1: Optional[str] = Form(None),
    top_2: Optional[str] = Form(None),
    top_3: Optional[str] = Form(None),
    ignore_list: Optional[str] = Form(None),
    major_risk: Optional[str] = Form(None),
    physiological_priority: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WeeklyDirectiveService(db)
    await service.save(
        user_id=current_user.id,
        weekly_theme=weekly_theme,
        top_1=top_1,
        top_2=top_2,
        top_3=top_3,
        ignore_list=ignore_list,
        major_risk=major_risk,
        physiological_priority=physiological_priority,
    )
    return RedirectResponse(url="/weekly", status_code=303)
