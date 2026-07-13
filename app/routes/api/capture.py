# app/routes/api/capture.py
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import EnergyLevel
from app.models.user import User
from app.repositories.capture_repo import CaptureRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.task_list_repo import TaskListRepository
from app.services.capture_service import CaptureService
from app.services.task_service import TaskService, TaskVerbError
from app.services.importancia_service import importancia_from_prioridade
from app.utils.auth import get_current_user
from app.utils.context_utils import resolve_active_context


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


@router.get("/capture/{capture_id}/decide", response_class=HTMLResponse)
async def decide_capture(
    capture_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = await CaptureRepository(db).get_by_id(capture_id, current_user.id)
    if not capture:
        raise HTTPException(status_code=404)

    active_context_id, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )
    active_projects = await ProjectRepository(db).get_active_by_user(current_user.id)

    # Listas para o popover "Listas" (padrão avulsas + Notas/Repositório + personalizadas).
    list_repo = TaskListRepository(db)
    await list_repo.ensure_system_lists(current_user.id)
    all_lists = await list_repo.get_active_by_user(current_user.id)
    notes_list = next((l for l in all_lists if l.system_key == "notes"), None)
    repo_list = next((l for l in all_lists if l.system_key == "repository"), None)
    custom_lists = [l for l in all_lists if l.system_key is None]

    # Contexto usado ao criar Task via popover (um clique): ativo → 1º disponível.
    default_context_id = active_context_id or (all_contexts[0].id if all_contexts else None)

    return templates.TemplateResponse(
        request,
        "partials/capture_decide.html",
        {
            "capture": capture,
            "all_contexts": all_contexts,
            "active_projects": active_projects,
            "active_context_id": active_context_id,
            "default_context_id": default_context_id,
            "notes_list": notes_list,
            "repo_list": repo_list,
            "custom_lists": custom_lists,
        },
    )


@router.get("/capture/{capture_id}/cancel-decide", response_class=HTMLResponse)
async def cancel_decide_capture(
    capture_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = await CaptureRepository(db).get_by_id(capture_id, current_user.id)
    if not capture:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/capture_item.html", {"capture": capture}
    )


@router.post("/process/{capture_id}", response_class=HTMLResponse)
async def process_capture(
    capture_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    action: str = Form(...),
    # Task fields
    title: Optional[str] = Form(None),
    task_project_id: Optional[str] = Form(None),
    task_context_id: Optional[str] = Form(None),
    task_energy: EnergyLevel = Form(EnergyLevel.medium),
    prioridade: str = Form("media"),
    is_quick_win: bool = Form(False),
    list_id: Optional[str] = Form(None),
    # Project fields
    project_name: Optional[str] = Form(None),
    project_objective: Optional[str] = Form(None),
    project_priority: int = Form(2),
    project_context_id: Optional[str] = Form(None),
    project_proxima_acao: Optional[str] = Form(None),
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
        err_target = {
            "HX-Retarget": f"#process-task-error-{capture_id}",
            "HX-Reswap": "innerHTML",
        }
        if not title or not title.strip():
            return HTMLResponse(
                '<p class="text-oriens-alert text-sm">Título é obrigatório.</p>',
                headers=err_target,
            )
        proj_id = _parse_int(task_project_id)
        ctx_id = _parse_int(task_context_id)
        # Tarefa de projeto herda contexto do projeto quando não fornecido
        if proj_id is not None and ctx_id is None:
            proj = await ProjectRepository(db).get_by_id(proj_id, current_user.id)
            if proj:
                ctx_id = proj.context_id
        # list_id só vale para tarefa avulsa de topo; valida ownership.
        lid = None
        if proj_id is None:
            lid_candidate = _parse_int(list_id)
            if lid_candidate is not None:
                owned = await TaskListRepository(db).get_by_id(lid_candidate, current_user.id)
                lid = owned.id if owned is not None else None
        if proj_id is None and ctx_id is None:
            return HTMLResponse(
                '<p class="text-oriens-alert text-sm">Escolha um contexto.</p>',
                headers=err_target,
            )
        importancia = None if proj_id is not None else importancia_from_prioridade(prioridade)
        try:
            await service.process_as_task(
                capture_id=capture_id,
                user_id=current_user.id,
                title=title.strip(),
                project_id=proj_id,
                energy=task_energy,
                is_quick_win=is_quick_win,
                context_id=ctx_id,
                importancia=importancia,
                list_id=lid,
                background_tasks=background_tasks,
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
            context_id=_parse_int(project_context_id),
            proxima_acao=project_proxima_acao.strip() if project_proxima_acao else None,
        )

    elif action == "discard":
        await service.discard(capture_id, current_user.id)

    return _removed_html()


@router.patch("/capture/{capture_id}", response_class=HTMLResponse)
async def update_capture_content(
    capture_id: int,
    request: Request,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = content.strip()
    if not content:
        return HTMLResponse("", status_code=422)
    updated = await CaptureRepository(db).update_content(capture_id, current_user.id, content)
    if not updated:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/capture_content_span.html", {"capture": updated}
    )


@router.patch("/capture/{capture_id}/resolve", response_class=HTMLResponse)
async def resolve_capture(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await CaptureService(db).resolve(capture_id, current_user.id)
    if item is None:
        raise HTTPException(status_code=404)
    return HTMLResponse("")


@router.patch("/capture/{capture_id}/discard", response_class=HTMLResponse)
async def discard_capture_to_trash(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await CaptureService(db).discard_to_trash(capture_id, current_user.id)
    if item is None:
        raise HTTPException(status_code=404)
    return HTMLResponse("")


@router.post("/capture/{capture_id}/restore", response_class=HTMLResponse)
async def restore_capture(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await CaptureService(db).restore(capture_id, current_user.id)
    if item is None:
        raise HTTPException(status_code=404)
    return HTMLResponse("")


@router.delete("/capture/{capture_id}", response_class=HTMLResponse)
async def hard_delete_capture(
    capture_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await CaptureService(db).hard_delete(capture_id, current_user.id)
    return HTMLResponse("")
