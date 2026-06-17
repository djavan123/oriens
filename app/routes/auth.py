from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.utils.auth import (
    COOKIE_NAME,
    TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.cookies.get(COOKIE_NAME):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "auth/login.html")


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await repo.get_by_email(email.lower().strip())
    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Email ou senha incorretos."},
            status_code=400,
        )
    token = create_access_token(user.id)
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        max_age=TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=get_settings().COOKIE_SECURE,
    )
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name}


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    if await repo.count() > 0:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse(request, "auth/setup.html")


@router.post("/setup")
async def setup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    if await repo.count() > 0:
        return RedirectResponse(url="/auth/login", status_code=302)
    user = await repo.create(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        name=name.strip(),
    )
    token = create_access_token(user.id)
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        max_age=TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=get_settings().COOKIE_SECURE,
    )
    return response
