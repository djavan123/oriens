# app/routes/api/capture.py
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import EnergyLevel
from app.models.user import User
from app.services.capture_service import CaptureService
from app.services.task_service import TaskVerbError
from app.utils.auth import get_current_user


def _parse_int(v: Optional[str]) -> Optional[int]:
    if not v or not v.strip():
        return None
    try:
        return int(v)
    except ValueError:
        return None

router = APIRouter(prefix="/api", tags=["api:capture"])


@router.post("/capture", response_class=HTMLResponse)
async def create_capture(
    request: Request,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = content.strip()
    if not content:
        return HTMLResponse(
            '<p class="text-oriens-alert text-xs">Conteúdo não pode ser vazio.</p>',
            headers={"HX-Retarget": "#capture-form-error", "HX-Reswap": "innerHTML"},
        )
    service = CaptureService(db)
    capture = await service.create(user_id=current_user.id, content=content)
    return templates.TemplateResponse(
        request, "partials/capture_item.html", {"capture": capture}
    )


@router.post("/process/{capture_id}", response_class=HTMLResponse)
async def process_capture(
    capture_id: int,
    request: Request,
    action: str = Form(...),
    # Task fields
    title: Optional[str] = Form(None),
    task_project_id: Optional[str] = Form(None),
    task_energy: EnergyLevel = Form(EnergyLevel.medium),
    is_quick_win: bool = Form(False),
    # Project fields
    project_name: Optional[str] = Form(None),
    project_objective: Optional[str] = Form(None),
    project_priority: int = Form(2),
    # Note fields
    note_content: Optional[str] = Form(None),
    note_project_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CaptureService(db)

    def _removed_html() -> HTMLResponse:
        return HTMLResponse(f'<div id="process-item-{capture_id}"></div>')

    def _task_error(exc: TaskVerbError) -> HTMLResponse:
        suggestions_html = "".join(
            f'<button type="button" '
            f"onclick=\"this.closest('form').querySelector('[name=title]').value='{s}';\" "
            f'class="block text-oriens-accent text-xs hover:opacity-80 text-left">{s}</button>'
            for s in exc.suggestions
        )
        html = (
            f'<p class="text-oriens-alert text-sm">{exc}</p>'
            f'<div class="mt-1 space-y-1">'
            f'<p class="text-oriens-secondary text-xs">Sugestões:</p>'
            f'{suggestions_html}'
            f'</div>'
        )
        return HTMLResponse(
            html,
            headers={
                "HX-Retarget": f"#process-task-error-{capture_id}",
                "HX-Reswap": "innerHTML",
            },
        )

    if action == "task":
        if not title or not title.strip():
            return HTMLResponse(
                '<p class="text-oriens-alert text-sm">Título é obrigatório.</p>',
                headers={
                    "HX-Retarget": f"#process-task-error-{capture_id}",
                    "HX-Reswap": "innerHTML",
                },
            )
        try:
            await service.process_as_task(
                capture_id=capture_id,
                user_id=current_user.id,
                title=title.strip(),
                project_id=_parse_int(task_project_id),
                energy=task_energy,
                is_quick_win=is_quick_win,
            )
        except TaskVerbError as e:
            return _task_error(e)
        except ValueError:
            raise HTTPException(status_code=404)

    elif action == "project":
        name = (project_name or "").strip()
        if not name:
            return HTMLResponse(
                '<p class="text-oriens-alert text-sm">Nome do projeto é obrigatório.</p>',
                headers={
                    "HX-Retarget": f"#process-project-error-{capture_id}",
                    "HX-Reswap": "innerHTML",
                },
            )
        await service.process_as_project(
            capture_id=capture_id,
            user_id=current_user.id,
            name=name,
            objective=project_objective.strip() if project_objective else None,
            priority=project_priority,
        )

    elif action == "note":
        content = (note_content or "").strip()
        if not content:
            return HTMLResponse(
                '<p class="text-oriens-alert text-sm">Conteúdo é obrigatório.</p>',
                headers={
                    "HX-Retarget": f"#process-note-error-{capture_id}",
                    "HX-Reswap": "innerHTML",
                },
            )
        await service.process_as_note(
            capture_id=capture_id,
            user_id=current_user.id,
            content=content,
            project_id=_parse_int(note_project_id),
        )

    elif action == "discard":
        await service.discard(capture_id, current_user.id)

    return _removed_html()
