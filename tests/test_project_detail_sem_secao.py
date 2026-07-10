from app.models.project import ProjectStatus
from app.repositories.project_section_repo import ProjectSectionRepository
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


async def test_detail_shows_tasks_without_section(client, db, test_user):
    """Tarefa de projeto sem seção tem de aparecer no bloco "Sem seção" —
    senão fica invisível e mesmo assim conta no progresso e na próxima ação."""
    p = await ProjectService(db).create(
        test_user.id, name="P", status=ProjectStatus.em_andamento
    )
    ts = TaskService(db)
    await ts.create(test_user.id, "órfã pendente", project_id=p.id)
    orfa_done = await ts.create(test_user.id, "órfã concluída", project_id=p.id)
    await ts.mark_done(orfa_done.id, test_user.id)

    r = await client.get(f"/projects/{p.id}")
    assert r.status_code == 200
    assert "órfã pendente" in r.text
    assert "órfã concluída" in r.text


async def test_detail_shows_both_sectioned_and_orphan_tasks(client, db, test_user):
    p = await ProjectService(db).create(
        test_user.id, name="P", status=ProjectStatus.em_andamento
    )
    sec = await ProjectSectionRepository(db).create(p.id, "Seção Alfa")
    ts = TaskService(db)
    await ts.create(test_user.id, "com seção", project_id=p.id, section_id=sec.id)
    await ts.create(test_user.id, "sem seção", project_id=p.id)

    r = await client.get(f"/projects/{p.id}")
    assert "Seção Alfa" in r.text
    assert "com seção" in r.text
    # O rótulo "Sem seção" só aparece quando o projeto já tem alguma seção.
    assert "Sem seção" in r.text
    assert "sem seção" in r.text
