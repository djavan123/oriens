# app/routes/api/tasks.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import EnergyLevel
from app.models.user import User
from app.repositories.task_list_repo import TaskListRepository
from app.services.link_title_service import fill_link_title
from app.services.task_service import TaskService, TaskVerbError
from app.services.importancia_service import importancia_from_prioridade
from app.utils.auth import get_current_user
from app.utils.link_meta import extract_url
from app.utils.time import utcnow


def _parse_date(v: Optional[str]) -> Optional[datetime]:
    if not v or not v.strip():
        return None
    try:
        return datetime.strptime(v.strip(), "%Y-%m-%d")
    except ValueError:
        return None


def _parse_int(v: Optional[str]) -> Optional[int]:
    if not v or not v.strip():
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _parse_list_id(v: Optional[str]) -> Optional[int]:
    if not v or v.strip().lower() in ("", "default", "null"):
        return None
    return _parse_int(v)


def _link_fields_now(title: str) -> tuple[dict, Optional[str]]:
    """Detecta URL no título (síncrono, barato). O título da página é buscado
    depois, em BackgroundTasks (fill_link_title) — a rede não bloqueia o request.

    Retorna (campos a gravar agora, url a buscar em background ou None).
    """
    url = extract_url(title)
    if not url:
        return {"link_url": None, "link_title": None, "link_checked_at": None}, None
    return {"link_url": url, "link_title": None, "link_checked_at": utcnow()}, url


def _parse_remind(date_str: Optional[str], time_str: Optional[str]) -> Optional[datetime]:
    """Combina Data + Hora num datetime. Sem data → None. Sem hora → 09:00."""
    if not date_str or not date_str.strip():
        return None
    t = (time_str or "").strip() or "09:00"
    try:
        return datetime.strptime(f"{date_str.strip()} {t}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None

router = APIRouter(prefix="/api/tasks", tags=["api:tasks"])


async def _task_row_response(request: Request, db: AsyncSession, task, current_user: User, is_new: bool = False):
    """Devolve o mesmo partial usado na renderização inicial da tarefa (Bug 2):
    tarefa de topo de projeto -> project_task_row.html; subtarefa de projeto ->
    project_subtask_row.html; avulsa -> task_item.html. Marca HX-Trigger para o
    painel de tarefas do projeto (progresso/próxima ação) resincronizar (Bug 3).

    `project_task_row.html` inclui o container de subtarefas como irmão do próprio
    card — correto ao ANEXAR uma tarefa nova (is_new=True), mas duplicaria esse
    container se usado para SUBSTITUIR (outerHTML) uma linha já existente na página
    (ela já tem seu próprio container de subtarefas ao lado). Por isso, ações sobre
    uma tarefa de topo já renderizada (concluir/bloquear/editar/etc.) devolvem corpo
    vazio: o HX-Trigger abaixo já resincroniza o painel inteiro com o markup certo.
    """
    if task.project_id is not None and task.parent_id is None:
        if is_new:
            from app.services.project_service import ProjectService
            from app.repositories.task_repo import TaskRepository
            project = await ProjectService(db).get_by_id(task.project_id, current_user.id)
            children = await TaskRepository(db).get_children_map(current_user.id, [task.id])
            response = templates.TemplateResponse(
                request,
                "partials/project_task_row.html",
                {"task": task, "project": project, "subtasks": {task.id: children.get(task.id, [])},
                 "draggable": True, "reload_on_done": False, "is_next": False},
            )
        else:
            response = HTMLResponse("")
    elif task.parent_id is not None and task.project_id is not None:
        response = templates.TemplateResponse(
            request, "partials/project_subtask_row.html", {"sub": task}
        )
    else:
        # Tarefa avulsa (em qualquer lista): sempre o mesmo item, com os mesmos flags.
        response = templates.TemplateResponse(
            request, "partials/task_item.html",
            {"task": task, "show_importancia": True, "show_link": True},
        )
    if task.project_id is not None:
        response.headers["HX-Trigger"] = "refreshProjectTasks"
    return response


def _verb_error_response(exc: TaskVerbError) -> HTMLResponse:
    suggestions_html = "".join(
        f'<button type="button" '
        f'onclick="this.closest(\'form\').querySelector(\'[name=title]\').value=\'{s}\';'
        f'this.closest(\'form\').querySelector(\'[name=title]\').focus()" '
        f'class="block text-oriens-accent text-xs hover:opacity-80 transition-opacity text-left">'
        f'{s}</button>'
        for s in exc.suggestions
    )
    html = (
        f'<p class="text-oriens-alert text-sm">{exc}</p>'
        f'<div class="mt-2 space-y-1">'
        f'<p class="text-oriens-secondary text-xs">Sugestões:</p>'
        f'{suggestions_html}'
        f'</div>'
    )
    return HTMLResponse(
        html,
        headers={"HX-Retarget": "#task-form-error", "HX-Reswap": "innerHTML"},
    )


@router.post("", response_class=HTMLResponse)
async def create_task(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    project_id: Optional[str] = Form(None),
    parent_id: Optional[str] = Form(None),
    section_id: Optional[str] = Form(None),
    energy: EnergyLevel = Form(EnergyLevel.medium),
    is_quick_win: bool = Form(False),
    context_id: Optional[str] = Form(None),
    prioridade: str = Form("media"),
    cognitive_load: Optional[str] = Form(None),
    deadline: Optional[str] = Form(None),
    responsavel_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    list_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.task import CognitiveLoad
    title = title.strip()
    if not title:
        return HTMLResponse(
            '<p class="text-oriens-alert text-sm">Título é obrigatório.</p>',
            headers={"HX-Retarget": "#task-form-error", "HX-Reswap": "innerHTML"},
        )
    extra = {}
    proj_id = _parse_int(project_id)
    pid = _parse_int(parent_id)
    project = None
    # Herança de contexto: tarefa dentro de um projeto herda o contexto dele.
    if proj_id is not None:
        from app.services.project_service import ProjectService
        from app.repositories.project_section_repo import ProjectSectionRepository
        project = await ProjectService(db).get_by_id(proj_id, current_user.id)
        if project is not None:
            extra["context_id"] = project.context_id
        # Validar e associar section_id quando fornecido
        sec_id = _parse_int(section_id)
        if sec_id is not None:
            sec = await ProjectSectionRepository(db).get_by_id(sec_id, proj_id)
            if sec is not None:
                extra["section_id"] = sec_id
    else:
        cid = _parse_int(context_id)
        # list_id só vale para tarefa avulsa de topo (nunca subtarefa/projeto).
        lid = None
        if pid is None:
            lid_raw = _parse_list_id(list_id)
            if lid_raw is not None:
                owned = await TaskListRepository(db).get_by_id(lid_raw, current_user.id)
                if owned is not None:
                    lid = owned.id
        # Tarefa avulsa de topo (em qualquer lista): contexto é obrigatório.
        # A lista é só agrupamento — uma task numa lista funciona como uma avulsa.
        if cid is None and pid is None:
            return HTMLResponse(
                '<p class="text-oriens-alert text-sm">Escolha um contexto.</p>',
                headers={"HX-Retarget": "#task-form-error", "HX-Reswap": "innerHTML"},
            )
        if cid is not None:
            extra["context_id"] = cid
        if lid is not None:
            extra["list_id"] = lid
    if pid is not None:
        extra["parent_id"] = pid
    if cognitive_load and cognitive_load in {c.value for c in CognitiveLoad}:
        extra["cognitive_load"] = CognitiveLoad(cognitive_load)
    dl = _parse_date(deadline)
    if dl is not None:
        extra["deadline"] = dl
    rid = _parse_int(responsavel_id)
    if rid is not None:
        extra["responsavel_id"] = rid
    if tags is not None:
        extra["tags"] = tags.strip() or None

    # Importância (SCRIPT 13): toda tarefa avulsa de topo recebe nota Alta/Média/Baixa,
    # esteja em qualquer lista. Tarefas de projeto e subtarefas ficam sem nota.
    is_subtask = pid is not None
    is_project_task = proj_id is not None
    if not is_subtask and not is_project_task:
        extra["importancia"] = importancia_from_prioridade(prioridade)
        extra["sem_nota"] = False

    link_fields, link_url = _link_fields_now(title)
    extra.update(link_fields)

    service = TaskService(db)
    try:
        task = await service.create(
            user_id=current_user.id,
            title=title,
            project_id=proj_id,
            energy=energy,
            is_quick_win=is_quick_win,
            **extra,
        )
    except TaskVerbError as e:
        return _verb_error_response(e)

    if link_url:
        background_tasks.add_task(fill_link_title, task.id, current_user.id, link_url)

    return await _task_row_response(request, db, task, current_user, is_new=True)


@router.patch("/{task_id}/done", response_class=HTMLResponse)
async def mark_done(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.mark_done(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)
    return await _task_row_response(request, db, task, current_user)


@router.patch("/{task_id}/blocked", response_class=HTMLResponse)
async def mark_blocked(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.mark_blocked(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)
    return await _task_row_response(request, db, task, current_user)


@router.patch("/{task_id}/pending", response_class=HTMLResponse)
async def mark_pending(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.mark_pending(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)
    return await _task_row_response(request, db, task, current_user)


@router.patch("/{task_id}/archive", response_class=HTMLResponse)
async def archive_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TaskService(db)
    task = await service.archive(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)
    headers = {"HX-Trigger": "refreshProjectTasks"} if task.project_id is not None else {}
    return HTMLResponse("", headers=headers)


@router.patch("/{task_id}/adiar", response_class=HTMLResponse)
async def adiar_task(
    task_id: int,
    deadline: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Adiar = escolher novo prazo. Atualiza o deadline e pede refresh da lista do Dashboard."""
    task = await TaskService(db).update(task_id, current_user.id, deadline=_parse_date(deadline))
    if not task:
        raise HTTPException(status_code=404)
    return HTMLResponse("", status_code=204, headers={"HX-Trigger": "refreshPriorities"})


@router.patch("/{task_id}", response_class=HTMLResponse)
async def update_task(
    task_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    energy: Optional[str] = Form(None),
    is_quick_win: bool = Form(False),
    deadline: Optional[str] = Form(None),
    responsavel_id: Optional[str] = Form(None),
    context_id: Optional[str] = Form(None),
    prioridade: str = Form("media"),
    tags: Optional[str] = Form(None),
    remind_date: Optional[str] = Form(None),
    remind_time: Optional[str] = Form(None),
    list_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = title.strip()
    if not title:
        return HTMLResponse(
            '<p class="text-oriens-alert text-xs">Título é obrigatório.</p>',
            headers={"HX-Retarget": f"#task-edit-error-{task_id}", "HX-Reswap": "innerHTML"},
        )
    service = TaskService(db)
    existing = await service.get_by_id(task_id, current_user.id)
    if not existing:
        raise HTTPException(status_code=404)

    kwargs: dict = {"title": title, "is_quick_win": is_quick_win, "deadline": _parse_date(deadline)}
    if description is not None:
        kwargs["description"] = description.strip() or None
    if energy and energy in {e.value for e in EnergyLevel}:
        kwargs["energy"] = EnergyLevel(energy)
    rid = _parse_int(responsavel_id)
    if rid is not None:
        kwargs["responsavel_id"] = rid
    # Contexto: tarefa de projeto herda do projeto (travado) → ignora o que vier.
    if existing.project_id is None and context_id is not None:
        kwargs["context_id"] = _parse_int(context_id)
    if tags is not None:
        kwargs["tags"] = tags.strip() or None
    # Lembrete: ao mudar, reseta os flags para poder disparar de novo.
    new_remind = _parse_remind(remind_date, remind_time)
    if new_remind != existing.remind_at:
        kwargs["remind_at"] = new_remind
        kwargs["reminder_telegram_sent"] = False
        kwargs["reminder_acked"] = False

    is_subtask = existing.parent_id is not None
    is_standalone_top = existing.project_id is None and not is_subtask

    # Lista (PARTE 6): mover entre listas só para tarefa avulsa de topo. Campo ausente
    # no form → não mexe. "Tarefas avulsas" → NULL. Lista com ownership válido → id.
    new_list_id = existing.list_id
    if is_standalone_top and list_id is not None:
        lid = _parse_list_id(list_id)
        if lid is None:
            new_list_id = None
        else:
            owned = await TaskListRepository(db).get_by_id(lid, current_user.id)
            new_list_id = owned.id if owned is not None else existing.list_id
        kwargs["list_id"] = new_list_id

    # Importância (SCRIPT 13): toda tarefa avulsa de topo recebe nota Alta/Média/Baixa,
    # em qualquer lista (a lista é só agrupamento).
    if is_standalone_top:
        kwargs["importancia"] = importancia_from_prioridade(prioridade)
        kwargs["sem_nota"] = False

    # Metadados de link (PARTE 4): recomputa só quando o título muda.
    link_url = None
    if title != existing.title:
        link_fields, link_url = _link_fields_now(title)
        kwargs.update(link_fields)

    try:
        task = await service.update(task_id, current_user.id, **kwargs)
    except TaskVerbError as e:
        return _verb_error_response(e)
    if not task:
        raise HTTPException(status_code=404)
    if link_url:
        background_tasks.add_task(fill_link_title, task.id, current_user.id, link_url)
    return await _task_row_response(request, db, task, current_user)


@router.get("/{task_id}/panel", response_class=HTMLResponse)
async def task_panel(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Painel de detalhe da tarefa (drawer): metadados + subtarefas, editável
    com autosave. Único fluxo de edição de tarefa (o form inline /edit e o
    drawer somente-leitura /detail foram removidos)."""
    from app.repositories.context_repo import ContextRepository
    from app.repositories.label_repo import LabelRepository
    from app.repositories.task_repo import TaskRepository
    from app.services.importancia_service import faixa_importancia
    from sqlalchemy import select as sa_select
    from app.models.user import User as UserModel

    service = TaskService(db)
    task = await service.get_by_id(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404)

    contexts = await ContextRepository(db).get_all_by_user(current_user.id)
    context_labels = {c.id: c.name for c in contexts}
    user_labels = await LabelRepository(db).get_all_by_user(current_user.id)
    users_result = await db.execute(sa_select(UserModel).order_by(UserModel.name))
    users = list(users_result.scalars().all())

    is_standalone_top = task.parent_id is None and task.project_id is None
    is_project_task = task.project_id is not None
    prioridade = faixa_importancia(task.importancia, task.sem_nota) or "media"

    # Lista (PARTE 6): seletor só para tarefa avulsa de topo (nunca projeto/subtarefa).
    notes_list = repo_list = None
    custom_lists: list = []
    if is_standalone_top:
        all_lists = await TaskListRepository(db).get_active_by_user(current_user.id)
        notes_list = next((l for l in all_lists if l.system_key == "notes"), None)
        repo_list = next((l for l in all_lists if l.system_key == "repository"), None)
        custom_lists = [l for l in all_lists if l.system_key is None]

    subtasks: list = []
    if task.parent_id is None:
        children = await TaskRepository(db).get_children_map(current_user.id, [task_id])
        subtasks = children.get(task_id, [])

    return templates.TemplateResponse(
        request,
        "partials/task_detail_panel.html",
        {"task": task, "contexts": contexts, "context_labels": context_labels,
         "user_labels": user_labels, "users": users,
         "show_prioridade": is_standalone_top, "is_project_task": is_project_task,
         "prioridade": prioridade, "is_standalone_top": is_standalone_top,
         "notes_list": notes_list, "repo_list": repo_list, "custom_lists": custom_lists,
         "subtasks": subtasks},
    )
