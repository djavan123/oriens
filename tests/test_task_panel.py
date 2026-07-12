from app.models.project import ProjectStatus
from app.repositories.context_repo import ContextRepository
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


async def test_panel_renders_for_standalone_task(client, db, test_user):
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")
    t = await TaskService(db).create(
        test_user.id, "Revisar contrato", context_id=ctx.id,
        importancia=5.0, sem_nota=False,
    )
    r = await client.get(f"/api/tasks/{t.id}/panel")
    assert r.status_code == 200
    assert "Revisar contrato" in r.text
    # Campos que corrigem o bug de rebaixamento + o campo novo.
    assert 'name="description"' in r.text
    assert 'name="prioridade"' in r.text
    assert 'name="list_id"' in r.text
    # Prioridade "Alta" (importancia 5.0) vem pré-selecionada — autosave não rebaixa.
    assert '<option value="alta" selected>' in r.text


async def test_panel_shows_maxima_selected(client, db, test_user):
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")
    t = await TaskService(db).create(
        test_user.id, "Urgente", context_id=ctx.id, importancia=6.0, sem_nota=False,
    )
    r = await client.get(f"/api/tasks/{t.id}/panel")
    assert '<option value="maxima" selected>' in r.text


async def test_panel_lists_subtasks(client, db, test_user):
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")
    parent = await TaskService(db).create(
        test_user.id, "Pai", context_id=ctx.id, importancia=5.0, sem_nota=False,
    )
    await TaskService(db).create(test_user.id, "Filha visível", parent_id=parent.id)
    r = await client.get(f"/api/tasks/{parent.id}/panel")
    assert "Filha visível" in r.text
    assert f'id="subtasks-{parent.id}"' in r.text


async def test_panel_404_for_missing_task(client):
    r = await client.get("/api/tasks/999999/panel")
    assert r.status_code == 404


async def test_patch_persists_description(client, db, test_user):
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")
    t = await TaskService(db).create(
        test_user.id, "Escrever proposta", context_id=ctx.id,
        importancia=5.0, sem_nota=False,
    )
    r = await client.patch(
        f"/api/tasks/{t.id}",
        data={"title": "Escrever proposta", "context_id": str(ctx.id),
              "prioridade": "alta", "description": "  detalhes da proposta  "},
    )
    assert r.status_code == 200
    refreshed = await TaskService(db).get_by_id(t.id, test_user.id)
    assert refreshed.description == "detalhes da proposta"


async def test_patch_without_description_field_keeps_existing(client, db, test_user):
    """Um PATCH que não envia o campo description não pode apagá-la."""
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")
    t = await TaskService(db).create(
        test_user.id, "Tarefa", context_id=ctx.id, importancia=5.0, sem_nota=False,
        description="mantida",
    )
    r = await client.patch(
        f"/api/tasks/{t.id}",
        data={"title": "Tarefa", "context_id": str(ctx.id), "prioridade": "alta"},
    )
    assert r.status_code == 200
    refreshed = await TaskService(db).get_by_id(t.id, test_user.id)
    assert refreshed.description == "mantida"


async def test_panel_patch_preserves_maxima(client, db, test_user):
    """Regressão: o painel envia `prioridade`, então editar outro campo não
    rebaixa uma tarefa Máxima (importancia 6.0) para Média."""
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")
    t = await TaskService(db).create(
        test_user.id, "Crítica", context_id=ctx.id, importancia=6.0, sem_nota=False,
    )
    # Simula o autosave do painel ao mudar a descrição, com prioridade preservada.
    r = await client.patch(
        f"/api/tasks/{t.id}",
        data={"title": "Crítica", "context_id": str(ctx.id),
              "prioridade": "maxima", "description": "nota", "energy": "high"},
    )
    assert r.status_code == 200
    refreshed = await TaskService(db).get_by_id(t.id, test_user.id)
    assert refreshed.importancia == 6.0


async def test_dashboard_title_opens_drawer(client, db, test_user):
    """A coluna 'Tarefas avulsas' do Dashboard abre o drawer no clique do título."""
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")
    t = await TaskService(db).create(
        test_user.id, "Avulsa clicável", context_id=ctx.id,
        importancia=5.0, sem_nota=False,
    )
    r = await client.get("/dashboard")
    assert r.status_code == 200
    assert f'/api/tasks/{t.id}/panel' in r.text
    assert 'id="task-drawer-content"' in r.text  # drawer global presente
    assert '/edit' not in r.text  # gatilho antigo some


async def test_project_detail_title_opens_drawer(client, db, test_user):
    p = await ProjectService(db).create(
        test_user.id, name="Proj", status=ProjectStatus.em_andamento
    )
    from app.repositories.project_section_repo import ProjectSectionRepository
    sec = await ProjectSectionRepository(db).create(p.id, "Seção")
    t = await TaskService(db).create(
        test_user.id, "Tarefa de proj", project_id=p.id, section_id=sec.id
    )
    r = await client.get(f"/projects/{p.id}")
    assert r.status_code == 200
    assert f'/api/tasks/{t.id}/panel' in r.text
    assert '/edit' not in r.text


async def test_panel_project_task_shows_no_list_selector(client, db, test_user):
    """Tarefa de projeto: sem seletor de lista (list_id só para avulsa de topo)."""
    p = await ProjectService(db).create(
        test_user.id, name="P", status=ProjectStatus.em_andamento
    )
    from app.repositories.project_section_repo import ProjectSectionRepository
    sec = await ProjectSectionRepository(db).create(p.id, "Seção")
    t = await TaskService(db).create(
        test_user.id, "Fazer", project_id=p.id, section_id=sec.id
    )
    r = await client.get(f"/api/tasks/{t.id}/panel")
    assert r.status_code == 200
    assert 'name="list_id"' not in r.text
