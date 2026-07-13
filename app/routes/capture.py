# app/routes/capture.py
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.capture_service import CaptureService
from app.utils.auth import get_current_user
from app.utils.context_utils import resolve_active_context

router = APIRouter(tags=["capture"])

# Página de itens da Caixa de Entrada / Lixeira (padrão "carregar mais").
PAGE_SIZE = 50


def _paginate(items: list, page_size: int, offset: int) -> tuple[list, bool, int]:
    """Recebe page_size+1 itens buscados; retorna (página, has_more, next_offset)."""
    has_more = len(items) > page_size
    return items[:page_size], has_more, offset + page_size


@router.get("/capture", response_class=HTMLResponse)
async def capture_inbox(
    request: Request,
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CaptureService(db)
    raw = await service.get_inbox(current_user.id, limit=PAGE_SIZE + 1, offset=offset)
    captures, has_more, next_offset = _paginate(raw, PAGE_SIZE, offset)

    page_ctx = {
        "captures": captures,
        "has_more": has_more,
        "next_offset": next_offset,
    }
    # Fragmento HTMX do "carregar mais": só os itens + próximo botão.
    if offset and request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/capture_page.html", page_ctx)

    _, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )

    return templates.TemplateResponse(
        request,
        "capture.html",
        {
            "user": current_user,
            "inbox_count": await service.count_inbox(current_user.id),
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
            **page_ctx,
        },
    )


@router.get("/lixeira", response_class=HTMLResponse)
async def lixeira(
    request: Request,
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CaptureService(db)
    if not offset:
        await service.cleanup_trash(current_user.id)
    raw = await service.get_trash(current_user.id, limit=PAGE_SIZE + 1, offset=offset)
    captures, has_more, next_offset = _paginate(raw, PAGE_SIZE, offset)

    page_ctx = {
        "captures": captures,
        "has_more": has_more,
        "next_offset": next_offset,
    }
    if offset and request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/trash_page.html", page_ctx)

    _, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )

    return templates.TemplateResponse(
        request,
        "lixeira.html",
        {
            "user": current_user,
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
            **page_ctx,
        },
    )


@router.get("/process")
async def process_redirect():
    return RedirectResponse(url="/capture", status_code=302)
