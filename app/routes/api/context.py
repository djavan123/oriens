# app/routes/api/context.py
import json
from typing import Optional
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.repositories.context_repo import ContextRepository
from app.services.capture_service import CaptureService
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/context", tags=["api:context"])

# Só estas telas fazem sentido como destino do re-render. Qualquer outra coisa
# vinda do header (inclusive uma URL de outro host, que o cliente controla)
# cai no Dashboard.
_TELAS = ("/dashboard", "/projects", "/lists", "/capture", "/settings", "/lixeira")


def _same_origin_path(current_url: Optional[str]) -> str:
    """Extrai caminho + query do `HX-Current-URL`, recusando destino externo.

    O header vem do navegador e é controlável pelo cliente; devolver ele cru
    dentro do `HX-Location` deixaria a rota mandar o htmx buscar outro host.
    """
    if not current_url:
        return "/dashboard"
    partes = urlsplit(current_url)
    caminho = partes.path or "/dashboard"
    if not caminho.startswith(_TELAS):
        return "/dashboard"
    return f"{caminho}?{partes.query}" if partes.query else caminho


def _context_response(context_id: str, current_url: Optional[str]) -> HTMLResponse:
    """Grava o cookie de contexto e manda o htmx re-renderizar a página atual.

    Antes isto devolvia `HX-Refresh: true`, ou seja, reload completo do
    documento a cada troca de contexto — e o contexto é o filtro usado o dia
    inteiro. Com `HX-Location` o htmx busca a mesma URL por AJAX e troca só o
    <body>, exatamente como o hx-boost do menu.

    Sem `select`: o htmx já extrai o <body> de uma resposta que é um documento
    completo. Passar `select: "body"` esvazia a página — o parser de HTML
    descarta a tag <body> ao montar o fragmento, então o seletor não casa com
    nada e o swap acontece com conteúdo vazio.
    """
    location = json.dumps({
        "path": _same_origin_path(current_url),
        "target": "body",
        "swap": "innerHTML",
    })
    response = HTMLResponse("", headers={"HX-Location": location})
    response.set_cookie(
        "oriens_context", context_id,
        httponly=True, samesite="lax",
        secure=get_settings().COOKIE_SECURE,
        max_age=60 * 60 * 12,
    )
    return response


async def _resolve_own_context(db: AsyncSession, user_id: int, context_id: str):
    """Valida o id e garante que o contexto pertence ao usuário.

    `get_all_by_user` já devolve os contextos globais (user_id NULL) mais os do
    próprio usuário — então basta exigir que o alvo esteja nessa lista. Antes a
    rota buscava por id direto, sem sessão nenhuma: qualquer um podia setar o
    cookie para um contexto personalizado de outro usuário.
    """
    try:
        cid = int(context_id)
    except (ValueError, TypeError):
        return None
    permitidos = await ContextRepository(db).get_all_by_user(user_id)
    return next((c for c in permitidos if c.id == cid), None)


@router.post("/switch", response_class=HTMLResponse)
async def switch_context(
    request: Request,
    context_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ctx = await _resolve_own_context(db, current_user.id, context_id)
    if not ctx:
        return HTMLResponse("", status_code=404)
    return _context_response(str(ctx.id), request.headers.get("HX-Current-URL"))


@router.post("/transition", response_class=HTMLResponse)
async def transition_context(
    request: Request,
    context_id: str = Form(...),
    pending_items: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ctx = await _resolve_own_context(db, current_user.id, context_id)
    if not ctx:
        return HTMLResponse("", status_code=404)

    if pending_items and pending_items.strip():
        service = CaptureService(db)
        lines = [l.strip() for l in pending_items.splitlines() if l.strip()]
        for line in lines:
            await service.create(user_id=current_user.id, content=line)

    return _context_response(str(ctx.id), request.headers.get("HX-Current-URL"))
