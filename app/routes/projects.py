from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.task import TaskStatus
from app.models.user import User
from sqlalchemy import select
from app.repositories.task_repo import TaskRepository
from app.repositories.project_comment_repo import ProjectCommentRepository
from app.repositories.project_attachment_repo import ProjectAttachmentRepository
from app.repositories.project_decision_repo import ProjectDecisionRepository
from app.repositories.project_risk_repo import ProjectRiskRepository
from app.repositories.project_audit_repo import ProjectAuditRepository
from app.repositories.project_timeline_repo import ProjectTimelineRepository
from app.repositories.label_repo import LabelRepository
from app.repositories.project_section_repo import ProjectSectionRepository
from app.services.project_service import ProjectService
from app.utils.auth import get_current_user
from app.utils.context_utils import resolve_active_context


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size // 1024} KB"
    return f"{size / (1024 * 1024):.1f} MB"

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_class=HTMLResponse)
async def projects_list(
    request: Request,
    filter: str = "active",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    context_id, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )
    context_labels = {ctx.id: ctx.label for ctx in all_contexts}

    if filter not in ("active", "archived", "all"):
        filter = "active"

    service = ProjectService(db)
    projects = await service.get_all(
        current_user.id,
        context_id=context_id,
        archived_only=(filter == "archived"),
        include_archived=(filter == "all"),
    )

    raw = await TaskRepository(db).progress_by_project(
        current_user.id, [p.id for p in projects]
    )
    progress = {
        pid: {"done": done, "total": total, "pct": round(done * 100 / total) if total else 0}
        for pid, (done, total) in raw.items()
    }

    exec_map = await service.get_executability(current_user.id, projects)

    users_result = await db.execute(select(User).order_by(User.name))
    users = list(users_result.scalars().all())
    responsavel_map = {u.id: u.name for u in users}

    return templates.TemplateResponse(
        request,
        "projects/list.html",
        {
            "user": current_user,
            "projects": projects,
            "current_filter": filter,
            "contexts": all_contexts,
            "context_labels": context_labels,
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
            "progress": progress,
            "exec_map": exec_map,
            "users": users,
            "responsavel_map": responsavel_map,
        },
    )


@router.get("/reports", response_class=HTMLResponse)
async def projects_reports(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )

    service = ProjectService(db)
    projects = await service.get_all(current_user.id)
    ids = [p.id for p in projects]

    task_repo = TaskRepository(db)
    progress_raw = await task_repo.progress_by_project(current_user.id, ids)
    overdue_raw = await task_repo.overdue_by_project(current_user.id, ids)

    decision_repo = ProjectDecisionRepository(db)
    risk_repo = ProjectRiskRepository(db)

    rows = []
    for p in projects:
        done, total = progress_raw.get(p.id, (0, 0))
        decisions = await decision_repo.get_by_project(p.id)
        rows.append({
            "project": p,
            "done": done,
            "total": total,
            "pct": round(done * 100 / total) if total else 0,
            "remaining": total - done,
            "overdue": overdue_raw.get(p.id, 0),
            "open_risks": await risk_repo.count_open(p.id),
            "decisions": len(decisions),
        })

    return templates.TemplateResponse(
        request,
        "projects/reports.html",
        {
            "user": current_user,
            "rows": rows,
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
        },
    )


async def _build_tasks_panel_context(
    db: AsyncSession, project, current_user: User
) -> dict:
    """Contexto do painel 'Tarefas' do detalhe do projeto (progresso, seções,
    tarefas, badge de próxima ação). Reaproveitado pelo render inicial da página
    (project_detail) e pelo endpoint de refresh via HTMX (project_tasks_panel)."""
    service = ProjectService(db)
    next_action = await service.get_project_next_action(project.id, current_user.id)

    task_repo = TaskRepository(db)
    all_tasks = await task_repo.get_all_by_user(current_user.id, project_id=project.id)
    pending_tasks = [t for t in all_tasks if t.status == TaskStatus.pending]
    blocked_tasks = [t for t in all_tasks if t.status == TaskStatus.blocked]
    done_tasks = [t for t in all_tasks if t.status == TaskStatus.done]

    subtasks = await task_repo.get_children_map(
        current_user.id, [t.id for t in all_tasks]
    )

    sections = await ProjectSectionRepository(db).get_all_by_project(project.id)
    section_ids = {s.id for s in sections}
    tasks_by_section: dict = {}
    for task in pending_tasks:
        key = task.section_id if (task.section_id in section_ids) else None
        tasks_by_section.setdefault(key, []).append(task)
    section_groups = [(s, tasks_by_section.get(s.id, [])) for s in sections]
    sem_secao_tasks = tasks_by_section.get(None, [])

    done_by_section: dict = {}
    for task in done_tasks:
        key = task.section_id if (task.section_id in section_ids) else None
        done_by_section.setdefault(key, []).append(task)

    blocked_by_section: dict = {}
    for task in blocked_tasks:
        key = task.section_id if (task.section_id in section_ids) else None
        blocked_by_section.setdefault(key, []).append(task)

    raw = await task_repo.progress_by_project(current_user.id, [project.id])
    done, total = raw.get(project.id, (0, 0))
    progress = {
        "done": done,
        "total": total,
        "pct": round(done * 100 / total) if total else 0,
    }

    users_result = await db.execute(select(User).order_by(User.name))
    users = list(users_result.scalars().all())
    responsavel_map = {u.id: u.name for u in users}

    return {
        "project": project,
        "next_action": next_action,
        "pending_tasks": pending_tasks,
        "blocked_tasks": blocked_tasks,
        "done_tasks": done_tasks,
        "sections": sections,
        "section_groups": section_groups,
        "sem_secao_tasks": sem_secao_tasks,
        "progress": progress,
        "subtasks": subtasks,
        "users": users,
        "responsavel_map": responsavel_map,
        "done_by_section": done_by_section,
        "blocked_by_section": blocked_by_section,
    }


@router.get("/{project_id}", response_class=HTMLResponse)
async def project_detail(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProjectService(db)
    project = await service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    panel_ctx = await _build_tasks_panel_context(db, project, current_user)

    _, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )
    context_labels = {ctx.id: ctx.label for ctx in all_contexts}

    user_labels = await LabelRepository(db).get_all_by_user(current_user.id)

    comments = await ProjectCommentRepository(db).get_by_project(project_id)
    attachments = await ProjectAttachmentRepository(db).get_by_project(project_id)
    decisions = await ProjectDecisionRepository(db).get_by_project(project_id)
    risks = await ProjectRiskRepository(db).get_by_project(project_id)

    audit = await ProjectAuditRepository(db).get_by_project(project_id)
    timeline = await ProjectTimelineRepository(db).get_by_project(project_id)

    return templates.TemplateResponse(
        request,
        "projects/detail.html",
        {
            "user": current_user,
            "contexts": all_contexts,
            "context_labels": context_labels,
            "active_context_obj": active_context_obj,
            "all_contexts": all_contexts,
            "user_labels": user_labels,
            "ai_enabled": get_settings().AI_ENABLED,
            "comments": comments,
            "attachments": attachments,
            "fmt_size": _fmt_size,
            "decisions": decisions,
            "risks": risks,
            "audit": audit,
            "timeline": timeline,
            **panel_ctx,
        },
    )


@router.get("/{project_id}/tasks-panel", response_class=HTMLResponse)
async def project_tasks_panel(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Refresh via HTMX (evento `refreshProjectTasks`) do painel de tarefas do
    detalhe do projeto: mantém progresso e badge 'Próxima ação' em dia sem
    depender de reload de página (BUG 3)."""
    service = ProjectService(db)
    project = await service.get_by_id(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    panel_ctx = await _build_tasks_panel_context(db, project, current_user)
    return templates.TemplateResponse(
        request, "partials/project_tasks_panel.html", panel_ctx
    )
