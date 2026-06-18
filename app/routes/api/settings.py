# app/routes/api/settings.py
from typing import Optional
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.context_repo import ContextRepository
from app.repositories.criterio_repo import CriterioContextoRepository
from app.repositories.label_repo import LabelRepository
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["api:settings"])


def _to_int(v: str, default: int = 1) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


@router.post("/criterios/{context_id}", response_class=HTMLResponse)
async def save_criterios(
    context_id: int,
    nome: list[str] = Form(default=[]),
    peso: list[str] = Form(default=[]),
    inverter: list[str] = Form(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Substitui todos os critérios do contexto pelos enviados (máx. 3, validado no repo)."""
    items: list[tuple[str, int, bool]] = []
    for i, n in enumerate(nome):
        p = _to_int(peso[i]) if i < len(peso) else 1
        inv = (inverter[i] == "true") if i < len(inverter) else False
        items.append((n, p, inv))
    await CriterioContextoRepository(db).replace_for_context(context_id, items)
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
