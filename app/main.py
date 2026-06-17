import asyncio
import contextlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

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


async def _reminder_loop():
    """Verifica lembretes vencidos a cada 60s e dispara o Telegram.
    Premissa: 1 worker uvicorn (Dockerfile padrão) — evita envios duplicados."""
    from app.database import AsyncSessionLocal
    from app.services.reminder_service import process_due_telegram
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await process_due_telegram(db)
        except Exception:
            pass
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # init_db() é idempotente (create_all com checkfirst) e seed_defaults() só
    # insere se vazio — seguro rodar sempre, inclusive em produção (DEBUG=false).
    from app.database import init_db, AsyncSessionLocal
    await init_db()
    from app.repositories.context_repo import ContextRepository
    async with AsyncSessionLocal() as db:
        await ContextRepository(db).seed_defaults()
    task = asyncio.create_task(_reminder_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


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
    return {"status": "ok"}
