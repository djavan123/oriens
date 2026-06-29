# app/routes/api/projects.py
import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import ProjectStatus
from app.models.user import User
from app.repositories.project_comment_repo import ProjectCommentRepository
from app.repositories.project_attachment_repo import ProjectAttachmentRepository
from app.repositories.project_decision_repo import ProjectDecisionRepository
from app.repositories.project_timeline_repo import ProjectTimelineRepository
from app.repositories.project_risk_repo import ProjectRiskRepository
from app.repositories.task_repo import TaskRepository
from app.repositories.project_section_repo import ProjectSectionRepository
from app.models.project_risk import RiskLevel, RiskStatus
from app.models.project_timeline import TimelineEventType
from app.repositories.context_repo import ContextRepository
from app.services.project_service import ProjectService
from app.utils.auth import get_current_user


class _TaskOrderPayload(BaseModel):
    task_ids: list[int]


class _SectionTasksPayload(BaseModel):
    section_id: Optional[int]
    task_ids: list[int]


class _SectionOrderPayload(BaseModel):
    section_ids: list[int]

router = APIRouter(prefix="/api/projects", tags=["api:projects"])

ATTACHMENTS_DIR = "/app/data/attachments"


def _parse_int(v: Optional[str]) -> Optional[int]:
    if not v or not v.strip():
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _parse_date(v: Optional[str]) -> Optional[datetime]:
    if not v or not v.strip():
        return None
    try:
        return datetime.strptime(v.strip(), "%Y-%m-%d")
    except ValueError:
        return None


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size // 1024} KB"
    return f"{size / (1024 * 1024):.1f} MB"


async def _assert_owns_project(db: AsyncSession, project_id: int, user_id: int) -> None:
    """Garante que o projeto existe e pertence ao usuário; 404 caso contrário."""
    if await ProjectService(db).get_by_id(project_id, user_id) is None:
        raise HTTPException(status_code=404)


@router.post("", response_class=HTMLResponse)
async def create_project(
    request: Request,
    name: str = Form(...),
    objective: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
    priority: int = Form(2),
    status: ProjectStatus = Form(ProjectStatus.nao_iniciado),
    notes: Optional[str] = Form(None),
    deadline: Optional[str] = Form(None),
    context_id: Optional[str] = Form(None),
    responsavel_id: Optional[str] = Form(None),
    proxima_acao: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = name.strip()
    if not name:
        return HTMLResponse(
            '<p id="project-form-error" class="text-oriens-alert text-sm mt-2">Nome do projeto é obrigatório.</p>',
            status_code=422,
        )
    if _parse_int(context_id) is None:
        return HTMLResponse(
            '<p id="project-form-error" class="text-oriens-alert text-sm mt-2">Contexto é obrigatório.</p>',
            status_code=422,
        )
    service = ProjectService(db)
    project = await service.create(
        user_id=current_user.id,
        name=name,
        objective=objective.strip() if objective else None,
        scope=scope.strip() if scope else None,
        priority=priority,
        status=status,
        notes=notes.strip() if notes else None,
        deadline=_parse_date(deadline),
        context_id=_parse_int(context_id),
        responsavel_id=_parse_int(responsavel_id),
        proxima_acao=proxima_acao.strip() if proxima_acao else None,
    )
    ctx = await ContextRepository(db).get_by_id(_parse_int(context_id))
    context_name = ctx.name if ctx else None
    return templates.TemplateResponse(
        request, "partials/project_row.html", {"project": project, "context_name": context_name}
    )


@router.patch("/{project_id}", response_class=HTMLResponse)
async def update_project(
    project_id: int,
    request: Request,
    status: Optional[ProjectStatus] = Form(None),
    name: Optional[str] = Form(None),
    priority: Optional[int] = Form(None),
    objective: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    deadline: Optional[str] = Form(None),
    context_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    proxima_acao: Optional[str] = Form(None),
    premissas: Optional[str] = Form(None),
    responsavel_id: Optional[str] = Form(None),
    archived: Optional[bool] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updates: dict = {}
    if status is not None:
        updates["status"] = status
    if name is not None:
        updates["name"] = name.strip()
    if priority is not None:
        updates["priority"] = priority
    if objective is not None:
        updates["objective"] = objective.strip() or None
    if scope is not None:
        updates["scope"] = scope.strip() or None
    if notes is not None:
        updates["notes"] = notes.strip() or None
    if deadline is not None:
        updates["deadline"] = _parse_date(deadline)
    # Contexto é obrigatório: nunca apagar (ignora valor vazio).
    if context_id is not None:
        cid = _parse_int(context_id)
        if cid is not None:
            updates["context_id"] = cid
    if tags is not None:
        updates["tags"] = tags.strip() or None
    if proxima_acao is not None:
        updates["proxima_acao"] = proxima_acao.strip() or None
    if premissas is not None:
        updates["premissas"] = premissas.strip() or None
    if responsavel_id is not None:
        updates["responsavel_id"] = _parse_int(responsavel_id)
    if archived is not None:
        updates["archived"] = archived

    service = ProjectService(db)
    project = await service.update(project_id, current_user.id, **updates)
    if not project:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/project_card.html", {"project": project}
    )


# ── Task order ────────────────────────────────────────────────────────────────

@router.patch("/{project_id}/task-order")
async def reorder_tasks(
    project_id: int,
    payload: _TaskOrderPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Persiste a ordem manual das tarefas de topo de um projeto.

    Recebe JSON {"task_ids": [1, 2, 3]} com os IDs na nova sequência.
    Valida: ownership do projeto, ownership de cada tarefa, todas pertencem
    ao mesmo projeto, nenhuma é subtarefa e nenhuma é tarefa avulsa.
    """
    await _assert_owns_project(db, project_id, current_user.id)
    if not payload.task_ids:
        raise HTTPException(status_code=422, detail="task_ids não pode ser vazio")
    ok = await TaskRepository(db).reorder_project_tasks(
        project_id, current_user.id, payload.task_ids
    )
    if not ok:
        raise HTTPException(
            status_code=422,
            detail="IDs inválidos: verifique ownership e pertencimento ao projeto",
        )
    return {"ok": True}


# ── Section tasks / section order ────────────────────────────────────────────

@router.patch("/{project_id}/section-tasks")
async def reorder_section_tasks(
    project_id: int,
    payload: _SectionTasksPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move e reordena tarefas dentro de (ou entre) seções.

    Recebe JSON {"section_id": null | int, "task_ids": [1, 2, 3]}.
    Atribui section_id e order_index (0, 1, 2…) a cada tarefa da lista.
    Valida: ownership do projeto, ownership de cada tarefa, sem subtarefas.
    """
    await _assert_owns_project(db, project_id, current_user.id)
    ok = await TaskRepository(db).reorder_section_tasks(
        project_id, current_user.id, payload.section_id, payload.task_ids
    )
    if not ok:
        raise HTTPException(
            status_code=422,
            detail="IDs inválidos: verifique ownership e pertencimento ao projeto",
        )
    return {"ok": True}


@router.patch("/{project_id}/section-order")
async def reorder_sections(
    project_id: int,
    payload: _SectionOrderPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reordena as seções de um projeto.

    Recebe JSON {"section_ids": [3, 1, 2]} com os IDs na nova sequência.
    Atribui order_index (0, 1, 2…) a cada seção. Valida pertencimento ao projeto.
    """
    await _assert_owns_project(db, project_id, current_user.id)
    ok = await ProjectSectionRepository(db).reorder_sections(project_id, payload.section_ids)
    if not ok:
        raise HTTPException(
            status_code=422,
            detail="IDs inválidos: verifique pertencimento ao projeto",
        )
    return {"ok": True}


# ── Sections ──────────────────────────────────────────────────────────────────

@router.post("/{project_id}/sections", response_class=HTMLResponse)
async def create_section(
    project_id: int,
    request: Request,
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_owns_project(db, project_id, current_user.id)
    name = name.strip()
    if not name:
        return HTMLResponse("")
    project = await ProjectService(db).get_by_id(project_id, current_user.id)
    section = await ProjectSectionRepository(db).create(project_id, name)
    return templates.TemplateResponse(
        request,
        "partials/project_section.html",
        {"section": section, "project": project},
    )


@router.patch("/{project_id}/sections/{section_id}", response_class=HTMLResponse)
async def rename_section(
    project_id: int,
    section_id: int,
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_owns_project(db, project_id, current_user.id)
    repo = ProjectSectionRepository(db)
    section = await repo.get_by_id(section_id, project_id)
    if not section:
        raise HTTPException(status_code=404)
    name = name.strip()
    if not name:
        return HTMLResponse(f'<span class="section-name-display">{section.name}</span>')
    section = await repo.update(section, name=name)
    return HTMLResponse(
        f'<span id="section-name-{section.id}" '
        f'class="text-oriens-secondary text-[11px] font-bold uppercase tracking-wide flex-1">'
        f'{section.name}</span>'
    )


@router.delete("/{project_id}/sections/{section_id}", response_class=HTMLResponse)
async def delete_section(
    project_id: int,
    section_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_owns_project(db, project_id, current_user.id)
    await ProjectSectionRepository(db).delete_with_nullify(section_id, project_id)
    return HTMLResponse("")


# ── Comments ──────────────────────────────────────────────────────────────────

@router.post("/{project_id}/comments", response_class=HTMLResponse)
async def add_comment(
    project_id: int,
    request: Request,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = content.strip()
    if not content:
        return HTMLResponse("")
    repo = ProjectCommentRepository(db)
    comment = await repo.create(project_id, current_user.id, content)
    return templates.TemplateResponse(
        request, "partials/project_comment.html", {"comment": comment, "user": current_user}
    )


@router.delete("/{project_id}/comments/{comment_id}", response_class=HTMLResponse)
async def delete_comment(
    project_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProjectCommentRepository(db)
    await repo.delete(comment_id, current_user.id)
    return HTMLResponse("")


# ── Attachments ───────────────────────────────────────────────────────────────

@router.post("/{project_id}/attachments", response_class=HTMLResponse)
async def upload_attachment(
    project_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        return HTMLResponse("")

    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest_dir = os.path.join(ATTACHMENTS_DIR, str(project_id))
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, stored_name)

    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    repo = ProjectAttachmentRepository(db)
    att = await repo.create(
        project_id=project_id,
        user_id=current_user.id,
        filename=stored_name,
        original_name=file.filename,
        size=len(contents),
    )
    return templates.TemplateResponse(
        request, "partials/project_attachment.html",
        {"att": att, "fmt_size": _fmt_size}
    )


@router.get("/{project_id}/attachments/{attachment_id}/download")
async def download_attachment(
    project_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProjectAttachmentRepository(db)
    att = await repo.get_by_id(attachment_id, current_user.id)
    if not att or att.project_id != project_id:
        raise HTTPException(status_code=404)
    path = os.path.join(ATTACHMENTS_DIR, str(project_id), att.filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    return FileResponse(path, filename=att.original_name)


@router.delete("/{project_id}/attachments/{attachment_id}", response_class=HTMLResponse)
async def delete_attachment(
    project_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProjectAttachmentRepository(db)
    att = await repo.delete(attachment_id, current_user.id)
    if att:
        path = os.path.join(ATTACHMENTS_DIR, str(project_id), att.filename)
        if os.path.exists(path):
            os.remove(path)
    return HTMLResponse("")


# ── Decisões ────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/decisions", response_class=HTMLResponse)
async def add_decision(
    project_id: int,
    request: Request,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_owns_project(db, project_id, current_user.id)
    content = content.strip()
    if not content:
        return HTMLResponse("")
    decision = await ProjectDecisionRepository(db).create(project_id, current_user.id, content)

    # Registra a decisão na cronologia do projeto.
    summary = content if len(content) <= 200 else content[:197] + "..."
    timeline = ProjectTimelineRepository(db)
    timeline.record(
        project_id, current_user.id, TimelineEventType.decision_recorded,
        f'Decisão registrada: "{summary}"'
    )
    await db.commit()

    return templates.TemplateResponse(
        request, "partials/project_decision.html", {"d": decision}
    )


@router.delete("/{project_id}/decisions/{decision_id}", response_class=HTMLResponse)
async def delete_decision(
    project_id: int,
    decision_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await ProjectDecisionRepository(db).delete(decision_id, current_user.id)
    return HTMLResponse("")


# ── Riscos ──────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/risks", response_class=HTMLResponse)
async def add_risk(
    project_id: int,
    request: Request,
    description: str = Form(...),
    impact: RiskLevel = Form(RiskLevel.medium),
    probability: RiskLevel = Form(RiskLevel.medium),
    mitigation: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    description = description.strip()
    if not description:
        return HTMLResponse("")
    repo = ProjectRiskRepository(db)
    risk = await repo.create(
        project_id=project_id,
        user_id=current_user.id,
        description=description,
        impact=impact,
        probability=probability,
        mitigation=mitigation.strip() if mitigation else None,
    )
    return templates.TemplateResponse(
        request, "partials/project_risk.html", {"r": risk}
    )


@router.patch("/{project_id}/risks/{risk_id}", response_class=HTMLResponse)
async def update_risk(
    project_id: int,
    risk_id: int,
    request: Request,
    status: Optional[RiskStatus] = Form(None),
    mitigation: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updates: dict = {}
    if status is not None:
        updates["status"] = status
    if mitigation is not None:
        updates["mitigation"] = mitigation.strip() or None
    repo = ProjectRiskRepository(db)
    risk = await repo.update(risk_id, current_user.id, **updates)
    if not risk or risk.project_id != project_id:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/project_risk.html", {"r": risk}
    )


@router.delete("/{project_id}/risks/{risk_id}", response_class=HTMLResponse)
async def delete_risk(
    project_id: int,
    risk_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProjectRiskRepository(db)
    await repo.delete(risk_id, current_user.id)
    return HTMLResponse("")
