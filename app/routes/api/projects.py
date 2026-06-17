# app/routes/api/projects.py
import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import ProjectStatus
from app.models.user import User
from app.repositories.project_comment_repo import ProjectCommentRepository
from app.repositories.project_attachment_repo import ProjectAttachmentRepository
from app.repositories.project_milestone_repo import ProjectMilestoneRepository
from app.repositories.project_risk_repo import ProjectRiskRepository
from app.models.project_risk import RiskLevel, RiskStatus
from app.services.project_service import ProjectService
from app.utils.auth import get_current_user

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = name.strip()
    if not name:
        return HTMLResponse(
            '<p id="project-form-error" class="text-oriens-alert text-sm mt-2">Nome do projeto é obrigatório.</p>',
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
    )
    return templates.TemplateResponse(
        request, "partials/project_card.html", {"project": project}
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
    if context_id is not None:
        updates["context_id"] = _parse_int(context_id)
    if tags is not None:
        updates["tags"] = tags.strip() or None
    if proxima_acao is not None:
        updates["proxima_acao"] = proxima_acao.strip() or None
    if premissas is not None:
        updates["premissas"] = premissas.strip() or None
    if responsavel_id is not None:
        updates["responsavel_id"] = _parse_int(responsavel_id)

    service = ProjectService(db)
    project = await service.update(project_id, current_user.id, **updates)
    if not project:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/project_card.html", {"project": project}
    )


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


# ── Milestones / Marcos ─────────────────────────────────────────────────────────

@router.post("/{project_id}/milestones", response_class=HTMLResponse)
async def add_milestone(
    project_id: int,
    request: Request,
    title: str = Form(...),
    due_date: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = title.strip()
    if not title:
        return HTMLResponse("")
    repo = ProjectMilestoneRepository(db)
    milestone = await repo.create(project_id, current_user.id, title, _parse_date(due_date))
    return templates.TemplateResponse(
        request, "partials/project_milestone.html", {"m": milestone}
    )


@router.patch("/{project_id}/milestones/{milestone_id}", response_class=HTMLResponse)
async def toggle_milestone(
    project_id: int,
    milestone_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProjectMilestoneRepository(db)
    milestone = await repo.toggle_done(milestone_id, current_user.id)
    if not milestone or milestone.project_id != project_id:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "partials/project_milestone.html", {"m": milestone}
    )


@router.delete("/{project_id}/milestones/{milestone_id}", response_class=HTMLResponse)
async def delete_milestone(
    project_id: int,
    milestone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProjectMilestoneRepository(db)
    await repo.delete(milestone_id, current_user.id)
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
