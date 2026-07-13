# app/routes/api/settings.py
import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.context_repo import ContextRepository
from app.repositories.label_repo import LabelRepository
from app.repositories.user_repo import UserRepository
from app.templates_env import templates
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["api:settings"])


@router.post("/telegram", response_class=HTMLResponse)
async def save_telegram_chat_id(
    telegram_chat_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Define o chat do Telegram do usuário (para lembretes + captura). Vazio limpa."""
    chat = telegram_chat_id.strip() or None
    repo = UserRepository(db)
    if chat is not None:
        owner = await repo.get_by_telegram_chat_id(chat)
        if owner is not None and owner.id != current_user.id:
            return HTMLResponse(
                '<p class="text-oriens-alert text-xs">Esse chat já está vinculado a outra conta.</p>',
                status_code=409,
            )
    await repo.set_telegram_chat_id(current_user.id, chat)
    return HTMLResponse("", headers={"HX-Refresh": "true"})


DEFAULT_LABEL_COLOR = "#5b8def"
_HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}")


@router.post("/labels", response_class=HTMLResponse)
async def create_label(
    request: Request,
    name: str = Form(...),
    color: str = Form(DEFAULT_LABEL_COLOR),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = name.strip()
    if not name:
        return HTMLResponse("")
    if not _HEX_COLOR_RE.fullmatch(color or ""):
        color = DEFAULT_LABEL_COLOR
    label = await LabelRepository(db).create(current_user.id, name, color)
    return templates.TemplateResponse(
        request, "partials/label_item.html", {"label": label}
    )


@router.delete("/labels/{label_id}", response_class=HTMLResponse)
async def delete_label(
    label_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await LabelRepository(db).delete(label_id, current_user.id)
    return HTMLResponse("")


@router.post("/contexts", response_class=HTMLResponse)
async def create_context(
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = name.strip()
    if not name:
        return HTMLResponse("")
    await ContextRepository(db).create(current_user.id, name)
    return HTMLResponse("", headers={"HX-Refresh": "true"})


@router.delete("/contexts/{context_id}", response_class=HTMLResponse)
async def delete_context(
    context_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await ContextRepository(db).delete(context_id, current_user.id)
    if not deleted:
        return HTMLResponse("", status_code=403)
    return HTMLResponse("", headers={"HX-Refresh": "true"})
