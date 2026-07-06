from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.task import EnergyLevel
from app.models.user import User
from app.repositories.label_repo import LabelRepository
from app.repositories.user_repo import UserRepository
from app.services.dashboard_service import DashboardService
from app.utils.auth import get_current_user
from app.utils.context_utils import resolve_active_context

router = APIRouter(tags=["dashboard"])

_MONTHS_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}
_DAYS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
_VALID_ENERGIES = {"high", "medium", "low"}


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    energy: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if energy is not None:
        energy_filter = energy if energy in _VALID_ENERGIES else None
    else:
        cookie_val = request.cookies.get("oriens_energy")
        energy_filter = cookie_val if cookie_val in _VALID_ENERGIES else None

    energy_enum = EnergyLevel(energy_filter) if energy_filter else None

    context_id, active_context_obj, all_contexts = await resolve_active_context(
        request, db, current_user.id
    )
    context_labels = {ctx.id: ctx.name for ctx in all_contexts}

    user_labels = await LabelRepository(db).get_all_by_user(current_user.id)

    service = DashboardService(db)
    data = await service.get_dashboard_data(
        current_user.id, energy_filter=energy_enum, context_id=context_id,
    )
    projects_focus = await service.get_projects_in_focus(
        current_user.id, context_id=context_id,
    )
    standalone_tasks = await service.get_standalone_tasks(
        current_user.id, energy=energy_enum, context_id=context_id,
    )
    now_action = service.pick_now_action(projects_focus, standalone_tasks)

    now = datetime.now()
    context = {
        "user": current_user,
        "data": data,
        "now_action": now_action,
        "projects_focus": projects_focus,
        "standalone_tasks": standalone_tasks,
        "energy_filter": energy_filter,
        "active_context_obj": active_context_obj,
        "active_context_id": context_id,
        "all_contexts": all_contexts,
        "context_labels": context_labels,
        "user_labels": user_labels,
        "current_date": f"{now.day} de {_MONTHS_PT[now.month]} de {now.year}",
        "day_of_week": _DAYS_PT[now.weekday()],
        "ai_enabled": get_settings().AI_ENABLED,
    }

    response = templates.TemplateResponse(request, "dashboard.html", context)

    if energy is not None:
        if energy in _VALID_ENERGIES:
            response.set_cookie(
                "oriens_energy", energy,
                httponly=True, samesite="lax",
                secure=get_settings().COOKIE_SECURE,
                max_age=60 * 60 * 8,
            )
        else:
            response.delete_cookie("oriens_energy")

    return response


@router.get("/dashboard/now", response_class=HTMLResponse)
async def dashboard_now(
    request: Request,
    energy: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    energy_filter = energy if energy in _VALID_ENERGIES else None
    energy_enum = EnergyLevel(energy_filter) if energy_filter else None
    context_id, _, all_contexts = await resolve_active_context(request, db, current_user.id)
    context_labels = {ctx.id: ctx.name for ctx in all_contexts}
    service = DashboardService(db)
    projects_focus = await service.get_projects_in_focus(current_user.id, context_id=context_id)
    standalone_tasks = await service.get_standalone_tasks(
        current_user.id, energy=energy_enum, context_id=context_id,
    )
    now_action = service.pick_now_action(projects_focus, standalone_tasks)
    return templates.TemplateResponse(
        request, "partials/dashboard_now.html",
        {"now_action": now_action, "context_labels": context_labels,
         "energy_filter": energy_filter},
    )


@router.get("/dashboard/projects-focus", response_class=HTMLResponse)
async def dashboard_projects_focus(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    context_id, _, _ = await resolve_active_context(request, db, current_user.id)
    projects_focus = await DashboardService(db).get_projects_in_focus(
        current_user.id, context_id=context_id,
    )
    return templates.TemplateResponse(
        request, "partials/dashboard_projects_focus.html",
        {"projects_focus": projects_focus},
    )


@router.get("/dashboard/standalone", response_class=HTMLResponse)
async def dashboard_standalone(
    request: Request,
    energy: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    energy_filter = energy if energy in _VALID_ENERGIES else None
    energy_enum = EnergyLevel(energy_filter) if energy_filter else None
    context_id, _, all_contexts = await resolve_active_context(request, db, current_user.id)
    context_labels = {ctx.id: ctx.name for ctx in all_contexts}
    standalone_tasks = await DashboardService(db).get_standalone_tasks(
        current_user.id, energy=energy_enum, context_id=context_id,
    )
    return templates.TemplateResponse(
        request, "partials/dashboard_standalone.html",
        {"standalone_tasks": standalone_tasks, "context_labels": context_labels,
         "all_contexts": all_contexts, "active_context_id": context_id,
         "energy_filter": energy_filter},
    )


@router.patch("/dashboard/foco", response_class=HTMLResponse)
async def update_foco(
    request: Request,
    foco: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await UserRepository(db).update_foco(current_user.id, foco.strip() or None)
    return templates.TemplateResponse(
        request, "partials/foco_do_dia.html", {"user": user}
    )
