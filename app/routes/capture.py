# app/routes/capture.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.services.capture_service import CaptureService
from app.utils.auth import get_current_user
from app.utils.context_utils import resolve_active_context

router = APIRouter(tags=["capture"])


@router.get("/capture", response_class=HTMLResponse)
async def capture_inbox(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CaptureService(db)
    captures = await service.get_inbox(current_user.id)

    _, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )

    return templates.TemplateResponse(
        request,
        "capture.html",
        {
            "user": current_user,
            "captures": captures,
            "pending_count": len(captures),
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
        },
    )


@router.get("/lixeira", response_class=HTMLResponse)
async def lixeira(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CaptureService(db)
    await service.cleanup_trash(current_user.id)
    captures = await service.get_trash(current_user.id)

    _, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )

    return templates.TemplateResponse(
        request,
        "lixeira.html",
        {
            "user": current_user,
            "captures": captures,
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
        },
    )


@router.get("/process", response_class=HTMLResponse)
async def process_inbox(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CaptureService(db)
    captures = await service.get_inbox(current_user.id)
    active_projects = await ProjectRepository(db).get_active_by_user(current_user.id)

    context_id, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )

    from app.repositories.criterio_repo import CriterioContextoRepository
    criterios_by_context = await CriterioContextoRepository(db).get_for_contexts(
        [c.id for c in all_contexts]
    )

    return templates.TemplateResponse(
        request,
        "process.html",
        {
            "user": current_user,
            "captures": captures,
            "active_projects": active_projects,
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
            "active_context_id": context_id,
            "criterios_by_context": criterios_by_context,
        },
    )
