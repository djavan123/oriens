# app/routes/api/lists.py
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.repository_repo import RepositoryRepository
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api", tags=["api:lists"])


@router.post("/repository", response_class=HTMLResponse)
async def create_repo_item(
    request: Request,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = content.strip()
    if not content:
        return HTMLResponse(
            '<p class="text-oriens-alert text-xs">Conteúdo não pode ser vazio.</p>',
            headers={"HX-Retarget": "#repo-form-error", "HX-Reswap": "innerHTML"},
        )
    item = await RepositoryRepository(db).create(user_id=current_user.id, content=content)
    return templates.TemplateResponse(
        request, "partials/repo_item.html", {"item": item}
    )


@router.delete("/repository/{item_id}", response_class=HTMLResponse)
async def delete_repo_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await RepositoryRepository(db).delete(item_id, current_user.id)
    return HTMLResponse("")
