# app/routes/api/settings.py
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.context_repo import ContextRepository
from app.repositories.label_repo import LabelRepository
from app.repositories.user_repo import UserRepository
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


def _label_html(label) -> str:
    color = label.color or "#2a2a2a"
    return (
        f'<div id="label-{label.id}" class="flex items-center gap-3 py-2.5 border-b border-oriens-divider last:border-0">'
        f'<span class="w-3 h-3 rounded-full flex-shrink-0" style="background:{color}"></span>'
        f'<span class="text-oriens-primary text-sm flex-1">{label.name}</span>'
        f'<button hx-delete="/api/settings/labels/{label.id}" hx-target="#label-{label.id}" hx-swap="outerHTML"'
        f' class="text-oriens-secondary text-xs hover:text-oriens-alert transition-colors">excluir</button>'
        f'</div>'
    )


@router.post("/labels", response_class=HTMLResponse)
async def create_label(
    name: str = Form(...),
    color: str = Form("#5b8def"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = name.strip()
    if not name:
        return HTMLResponse("")
    label = await LabelRepository(db).create(current_user.id, name, color or None)
    return HTMLResponse(_label_html(label))


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
