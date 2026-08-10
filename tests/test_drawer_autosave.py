# tests/test_drawer_autosave.py
"""Autosave do drawer de tarefa.

Regressão coberta aqui: o autosave usava `hx-target="#task-{id}"`. Nos cards de
"Projetos em foco" do Dashboard esse elemento nunca existiu, então o PATCH salvava
no banco e a tela não mudava absolutamente nada — sem spinner, sem confirmação.
Agora a resposta é 204 + HX-Trigger, e cada tela resincroniza o bloco que tem.
"""
import pytest

from app.models.project import ProjectStatus
from app.repositories.context_repo import ContextRepository
from app.repositories.project_section_repo import ProjectSectionRepository
from app.services.project_service import ProjectService
from app.services.task_service import TaskService

pytestmark = pytest.mark.asyncio


async def test_autosave_avisa_por_evento_em_vez_de_trocar_a_linha(client, db, test_user):
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")
    t = await TaskService(db).create(
        test_user.id, "Avulsa", context_id=ctx.id, importancia=5.0, sem_nota=False,
    )

    r = await client.patch(
        f"/api/tasks/{t.id}",
        data={"title": "Avulsa", "context_id": str(ctx.id), "prioridade": "alta",
              "energy": "high"},
    )

    assert r.status_code == 204
    assert r.text == ""                       # nada para trocar no lugar
    eventos = r.headers["HX-Trigger"]
    # Os blocos que existem em cada tela onde o drawer pode ser aberto.
    assert "refreshProjectsFocus" in eventos  # Dashboard — projetos em foco
    assert "refreshPriorities" in eventos     # Dashboard — tarefas avulsas
    assert "refreshLists" in eventos          # /lists


async def test_tarefa_de_projeto_tambem_resincroniza_o_painel(client, db, test_user):
    p = await ProjectService(db).create(
        test_user.id, name="Proj", status=ProjectStatus.em_andamento
    )
    sec = await ProjectSectionRepository(db).create(p.id, "Seção")
    t = await TaskService(db).create(
        test_user.id, "Ação", project_id=p.id, section_id=sec.id
    )

    r = await client.patch(
        f"/api/tasks/{t.id}", data={"title": "Ação", "prioridade": "media"}
    )

    assert r.status_code == 204
    assert "refreshProjectTasks" in r.headers["HX-Trigger"]


async def test_titulo_vazio_continua_devolvendo_erro_no_drawer(client, db, test_user):
    """O caminho de erro não pode virar 204: precisa aparecer no painel."""
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")
    t = await TaskService(db).create(
        test_user.id, "Tem título", context_id=ctx.id, importancia=5.0, sem_nota=False,
    )

    r = await client.patch(
        f"/api/tasks/{t.id}",
        data={"title": "   ", "context_id": str(ctx.id), "prioridade": "alta"},
    )

    assert r.status_code == 200
    assert r.headers["HX-Retarget"] == f"#task-edit-error-{t.id}"
    assert "obrigatório" in r.text


async def test_lists_serve_fragmento_para_o_refresh(client, db, test_user):
    """`refreshLists` recarrega #list-tasks via /lists?fragment=1 — só os itens."""
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")
    await TaskService(db).create(
        test_user.id, "Item da lista", context_id=ctx.id, importancia=5.0, sem_nota=False,
    )

    r = await client.get("/lists?fragment=1", headers={"HX-Request": "true"})

    assert r.status_code == 200
    assert "Item da lista" in r.text
    assert "<aside" not in r.text   # fragmento, não a página inteira
