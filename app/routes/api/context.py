# app/routes/api/context.py
from typing import Optional
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.repositories.context_repo import ContextRepository
from app.services.capture_service import CaptureService
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/context", tags=["api:context"])


def _context_response(context_id: str) -> HTMLResponse:
    response = HTMLResponse("", headers={"HX-Refresh": "true"})
    response.set_cookie(
        "oriens_context", context_id,
        httponly=True, samesite="lax",
        secure=get_settings().COOKIE_SECURE,
        max_age=60 * 60 * 12,
    )
    return response


@router.post("/switch", response_class=HTMLResponse)
async def switch_context(
    context_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = int(context_id)
    except (ValueError, TypeError):
        return HTMLResponse("", status_code=400)
    ctx = await ContextRepository(db).get_by_id(cid)
    if not ctx:
        return HTMLResponse("", status_code=404)
    return _context_response(str(cid))


@router.post("/transition", response_class=HTMLResponse)
async def transition_context(
    context_id: str = Form(...),
    pending_items: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        cid = int(context_id)
    except (ValueError, TypeError):
        return HTMLResponse("", status_code=400)
    ctx = await ContextRepository(db).get_by_id(cid)
    if not ctx:
        return HTMLResponse("", status_code=404)

    if pending_items and pending_items.strip():
        service = CaptureService(db)
        lines = [l.strip() for l in pending_items.splitlines() if l.strip()]
        for line in lines:
            await service.create(user_id=current_user.id, content=line)

    return _context_response(str(cid))
