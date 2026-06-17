# app/routes/settings.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.label_repo import LabelRepository
from app.templates_env import templates
from app.utils.auth import get_current_user
from app.utils.context_utils import resolve_active_context

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    labels = await LabelRepository(db).get_all_by_user(current_user.id)
    _, active_context_obj, all_contexts = await resolve_active_context(request, db, current_user.id)
    user_contexts = [c for c in all_contexts if c.user_id is not None]
    default_contexts = [c for c in all_contexts if c.user_id is None]

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "user": current_user,
            "labels": labels,
            "all_contexts": all_contexts,
            "active_context_obj": active_context_obj,
            "user_contexts": user_contexts,
            "default_contexts": default_contexts,
        },
    )
