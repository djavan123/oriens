# tests/test_pagination.py
"""Paginação "carregar mais" (Caixa de Entrada, Lixeira, Listas) e reports sem N+1."""
import pytest

from app.repositories.capture_repo import CaptureRepository
from app.repositories.project_decision_repo import ProjectDecisionRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.project_risk_repo import ProjectRiskRepository
from app.models.project import ProjectStatus
from app.models.project_risk import RiskLevel


@pytest.mark.asyncio
async def test_inbox_first_page_has_load_more(client, db, test_user):
    repo = CaptureRepository(db)
    for i in range(60):
        await repo.create(test_user.id, f"captura {i}")

    resp = await client.get("/capture")
    assert resp.status_code == 200
    assert "Carregar mais" in resp.text
    assert "60 itens" in resp.text  # contador usa COUNT real, não o tamanho da página


@pytest.mark.asyncio
async def test_inbox_second_page_is_fragment_without_button(client, db, test_user):
    repo = CaptureRepository(db)
    for i in range(60):
        await repo.create(test_user.id, f"captura {i}")

    resp = await client.get("/capture?offset=50", headers={"HX-Request": "true"})
    assert resp.status_code == 200
    # Fragmento: sem o layout da página, só itens; 10 restantes → sem botão.
    assert "<html" not in resp.text.lower()
    assert "Carregar mais" not in resp.text
    assert resp.text.count('id="capture-') >= 10


@pytest.mark.asyncio
async def test_inbox_under_page_size_has_no_button(client, db, test_user):
    repo = CaptureRepository(db)
    for i in range(3):
        await repo.create(test_user.id, f"captura {i}")
    resp = await client.get("/capture")
    assert resp.status_code == 200
    assert "Carregar mais" not in resp.text


@pytest.mark.asyncio
async def test_trash_pagination(client, db, test_user):
    repo = CaptureRepository(db)
    for i in range(55):
        item = await repo.create(test_user.id, f"lixo {i}")
        await repo.discard_to_trash(item.id, test_user.id)

    resp = await client.get("/lixeira")
    assert resp.status_code == 200
    assert "Carregar mais" in resp.text

    resp2 = await client.get("/lixeira?offset=50", headers={"HX-Request": "true"})
    assert resp2.status_code == 200
    assert "Carregar mais" not in resp2.text


@pytest.mark.asyncio
async def test_reports_counts_aggregated(client, db, test_user):
    """Reports usa contagens agregadas (GROUP BY) — valores por projeto corretos."""
    proj_repo = ProjectRepository(db)
    p1 = await proj_repo.create(
        test_user.id, name="Projeto A", status=ProjectStatus.em_andamento, priority=1
    )
    p2 = await proj_repo.create(
        test_user.id, name="Projeto B", status=ProjectStatus.em_andamento, priority=1
    )

    dec_repo = ProjectDecisionRepository(db)
    await dec_repo.create(p1.id, test_user.id, "decisão 1")
    await dec_repo.create(p1.id, test_user.id, "decisão 2")

    risk_repo = ProjectRiskRepository(db)
    await risk_repo.create(p2.id, test_user.id, "risco", RiskLevel.high, RiskLevel.medium)

    decisions = await dec_repo.count_by_projects([p1.id, p2.id])
    risks = await risk_repo.count_open_by_projects([p1.id, p2.id])
    assert decisions == {p1.id: 2}
    assert risks == {p2.id: 1}

    resp = await client.get("/projects/reports")
    assert resp.status_code == 200
    assert "Projeto A" in resp.text and "Projeto B" in resp.text
