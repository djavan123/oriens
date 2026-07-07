import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.logging_setup import configure_logging, check_production_secrets

configure_logging()
logger = logging.getLogger("oriens.main")

from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.projects import router as projects_router
from app.routes.capture import router as capture_router
from app.routes.settings import router as settings_router
from app.routes.api.projects import router as api_projects_router
from app.routes.api.tasks import router as api_tasks_router
from app.routes.api.capture import router as api_capture_router
from app.routes.api.ai import router as api_ai_router
from app.routes.api.context import router as api_context_router
from app.routes.api.settings import router as api_settings_router
from app.routes.api.reminders import router as api_reminders_router
from app.routes.weekly import router as weekly_router
from app.routes.lists import router as lists_router
from app.routes.api.lists import router as api_lists_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # init_db() é idempotente (create_all com checkfirst + advisory lock no PG) e
    # seed_defaults() só insere se vazio — seguro rodar em todo worker do web.
    # Os loops de fundo (lembretes/Telegram) rodam no processo `app.worker`, não aqui,
    # para que o web possa escalar com múltiplos workers sem duplicar envios.
    check_production_secrets()
    from app.database import init_db
    await init_db()  # migração + seed de contextos, guardados por advisory lock
    yield


app = FastAPI(title="Oriens", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(projects_router)
app.include_router(capture_router)
app.include_router(settings_router)
app.include_router(api_projects_router)
app.include_router(api_tasks_router)
app.include_router(api_capture_router)
app.include_router(api_ai_router)
app.include_router(api_context_router)
app.include_router(api_settings_router)
app.include_router(api_reminders_router)
app.include_router(weekly_router)
app.include_router(lists_router)
app.include_router(api_lists_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        path = request.url.path
        if not path.startswith("/api/") and not path.startswith("/auth/"):
            return RedirectResponse(url="/auth/login", status_code=302)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/health")
async def health():
    """Healthcheck com ping no banco — detecta app 'de pé' mas sem DB."""
    from sqlalchemy import text
    from app.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Healthcheck falhou ao consultar o banco")
        return JSONResponse(status_code=503, content={"status": "error", "db": "down"})
    return {"status": "ok"}
