from app.utils.auth import COOKIE_NAME

from tests.conftest import TEST_EMAIL, TEST_PASSWORD


async def test_health(anon_client):
    r = await anon_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_dashboard_requires_auth(anon_client):
    r = await anon_client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/login" in r.headers["location"]


async def test_dashboard_authed(client):
    r = await client.get("/dashboard")
    assert r.status_code == 200


async def test_projects_page_authed(client):
    r = await client.get("/projects")
    assert r.status_code == 200


async def test_login_sets_cookie(anon_client, test_user):
    r = await anon_client.post(
        "/auth/login",
        data={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert COOKIE_NAME in r.cookies


async def test_login_wrong_password(anon_client, test_user):
    r = await anon_client.post(
        "/auth/login",
        data={"email": TEST_EMAIL, "password": "errada"},
    )
    assert r.status_code == 400
