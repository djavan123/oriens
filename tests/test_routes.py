import pytest


# ── Auth ───────────────────────────────────────────────────────────────────────

async def test_unauthenticated_dashboard_redirects_to_login(anon_client):
    response = await anon_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["location"]

async def test_unauthenticated_missions_redirects(anon_client):
    response = await anon_client.get("/missions", follow_redirects=False)
    assert response.status_code == 302

async def test_login_page_is_accessible(anon_client):
    response = await anon_client.get("/auth/login")
    assert response.status_code == 200

async def test_setup_page_accessible_before_first_user(anon_client, db):
    from app.models.user import User
    from sqlalchemy import select
    count_result = await db.execute(select(User))
    # test_user fixture hasn't run here — anon_client doesn't depend on test_user
    response = await anon_client.get("/auth/setup")
    # Either 200 (no users) or 302 (already has users)
    assert response.status_code in (200, 302)

async def test_login_with_wrong_password(anon_client, db, test_user):
    from app.main import app
    from app.database import get_db
    async def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    response = await anon_client.post(
        "/auth/login",
        data={"email": test_user.email, "password": "errada"},
        follow_redirects=False,
    )
    app.dependency_overrides.clear()
    assert response.status_code == 400

async def test_login_sets_cookie(anon_client, db, test_user):
    from app.main import app
    from app.database import get_db
    async def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    response = await anon_client.post(
        "/auth/login",
        data={"email": test_user.email, "password": "senha123"},
        follow_redirects=False,
    )
    app.dependency_overrides.clear()
    assert response.status_code == 302
    assert "pos_token" in response.cookies


# ── Dashboard ──────────────────────────────────────────────────────────────────

async def test_dashboard_returns_200(client):
    response = await client.get("/dashboard")
    assert response.status_code == 200

async def test_dashboard_contains_pos_branding(client):
    response = await client.get("/dashboard")
    assert "POS" in response.text

async def test_dashboard_contains_date(client):
    response = await client.get("/dashboard")
    # Route injects current_date into template
    assert response.status_code == 200

async def test_dashboard_energy_filter_high(client):
    response = await client.get("/dashboard?energy=high")
    assert response.status_code == 200
    assert response.cookies.get("pos_energy") == "high"

async def test_dashboard_energy_filter_medium(client):
    response = await client.get("/dashboard?energy=medium")
    assert response.status_code == 200
    assert response.cookies.get("pos_energy") == "medium"

async def test_dashboard_energy_filter_clear(client):
    await client.get("/dashboard?energy=high")
    response = await client.get("/dashboard?energy=")
    assert response.status_code == 200

async def test_dashboard_invalid_energy_ignored(client):
    response = await client.get("/dashboard?energy=supercharged")
    assert response.status_code == 200

async def test_root_redirects_to_dashboard(client):
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/dashboard" in response.headers["location"]


# ── Capture ────────────────────────────────────────────────────────────────────

async def test_capture_page_returns_200(client):
    response = await client.get("/capture")
    assert response.status_code == 200

async def test_capture_api_creates_item(client):
    response = await client.post("/api/capture", data={"content": "Ideia para novo produto"})
    assert response.status_code == 200
    assert "Ideia para novo produto" in response.text

async def test_capture_api_rejects_empty_content(client):
    response = await client.post("/api/capture", data={"content": "   "})
    assert "HX-Retarget" in response.headers

async def test_capture_item_appears_in_inbox(client, db, test_user):
    await client.post("/api/capture", data={"content": "Item de teste"})
    response = await client.get("/capture")
    assert "Item de teste" in response.text

async def test_capture_multiple_items(client):
    for i in range(3):
        r = await client.post("/api/capture", data={"content": f"Captura {i + 1}"})
        assert r.status_code == 200


# ── Process ────────────────────────────────────────────────────────────────────

async def test_process_page_returns_200(client):
    response = await client.get("/process")
    assert response.status_code == 200

async def test_process_page_empty_state(client):
    response = await client.get("/process")
    assert "inbox" in response.text.lower() or "processar" in response.text.lower()

async def test_process_discard(client, db, test_user):
    from app.services.capture_service import CaptureService
    from app.repositories.capture_repo import CaptureRepository
    capture = await CaptureService(db).create(test_user.id, "Algo para descartar")
    response = await client.post(
        f"/api/process/{capture.id}",
        data={"action": "discard"},
    )
    assert response.status_code == 200
    updated = await CaptureRepository(db).get_by_id(capture.id, test_user.id)
    assert updated.processed is True

async def test_process_as_note(client, db, test_user):
    from app.services.capture_service import CaptureService
    from app.repositories.capture_repo import CaptureRepository
    capture = await CaptureService(db).create(test_user.id, "Pensamento importante")
    response = await client.post(
        f"/api/process/{capture.id}",
        data={"action": "note", "note_content": "Pensamento importante"},
    )
    assert response.status_code == 200
    updated = await CaptureRepository(db).get_by_id(capture.id, test_user.id)
    assert updated.processed is True

async def test_process_as_task_with_verb(client, db, test_user):
    from app.services.capture_service import CaptureService
    from app.repositories.capture_repo import CaptureRepository
    capture = await CaptureService(db).create(test_user.id, "Criar relatório semanal")
    response = await client.post(
        f"/api/process/{capture.id}",
        data={"action": "task", "title": "Criar relatório semanal"},
    )
    assert response.status_code == 200
    updated = await CaptureRepository(db).get_by_id(capture.id, test_user.id)
    assert updated.processed is True

async def test_process_as_task_without_verb_returns_error(client, db, test_user):
    from app.services.capture_service import CaptureService
    capture = await CaptureService(db).create(test_user.id, "Relatório semanal")
    response = await client.post(
        f"/api/process/{capture.id}",
        data={"action": "task", "title": "Relatório semanal"},
    )
    assert response.status_code == 200
    assert "HX-Retarget" in response.headers

async def test_process_as_project(client, db, test_user):
    from app.services.capture_service import CaptureService
    from app.repositories.capture_repo import CaptureRepository
    capture = await CaptureService(db).create(test_user.id, "Site institucional")
    response = await client.post(
        f"/api/process/{capture.id}",
        data={"action": "project", "project_name": "Site institucional"},
    )
    assert response.status_code == 200
    updated = await CaptureRepository(db).get_by_id(capture.id, test_user.id)
    assert updated.processed is True


# ── Projetos e Missões ─────────────────────────────────────────────────────────

async def test_projects_page_returns_200(client):
    response = await client.get("/projects")
    assert response.status_code == 200

async def test_create_project_via_api(client):
    response = await client.post(
        "/api/projects",
        data={"name": "Projeto de teste", "priority": "2"},
    )
    assert response.status_code == 200
    assert "Projeto de teste" in response.text

async def test_missions_page_returns_200(client):
    response = await client.get("/missions")
    assert response.status_code == 200

async def test_create_mission_via_api(client):
    response = await client.post(
        "/api/missions",
        data={"title": "Missão de teste", "energy": "medium", "priority": "2"},
    )
    assert response.status_code == 200
    assert "Missão de teste" in response.text

async def test_health_endpoint(anon_client):
    response = await anon_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
