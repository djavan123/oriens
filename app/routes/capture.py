# app/routes/capture.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
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


@router.get("/process")
async def process_redirect():
    return RedirectResponse(url="/capture", status_code=302)
