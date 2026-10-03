from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.config import ROOT, get_settings
from app.db import get_session
from app.models import LoudMeter, Streak, User
from app.services.auth import (
    SESSION_COOKIE,
    SESSION_SECONDS,
    hash_password,
    normalize_username,
    request_user,
    signed_token,
    valid_username,
    verify_password,
)
from app.services.i18n import context_for

router = APIRouter()
templates = Jinja2Templates(directory=ROOT / "app" / "templates")


def _redirect_with_cookie(user: User) -> RedirectResponse:
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        signed_token("session", user.id or 0),
        max_age=SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=get_settings().app_env == "production",
    )
    return response


@router.get("/account")
def account(request: Request, session: Session = Depends(get_session)):
    user = request_user(request, session)
    loud = session.exec(
        select(LoudMeter).where(
            LoudMeter.user_id == user.id, LoudMeter.date == date.today()
        )
    ).first()
    context = {
        **context_for(request),
        "page": "account",
        "user": user,
        "loud_seconds": loud.total_seconds if loud else 0,
        "error": request.query_params.get("error", ""),
    }
    return templates.TemplateResponse(request, "account.html", context)


@router.post("/account/register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    nickname: str = Form(...),
    session: Session = Depends(get_session),
):
    username = normalize_username(username)
    if not valid_username(username):
        return RedirectResponse("/account?error=username", status_code=303)
    if len(password) < 6 or len(password) > 128:
        return RedirectResponse("/account?error=password", status_code=303)
    if session.exec(select(User).where(User.username == username)).first():
        return RedirectResponse("/account?error=exists", status_code=303)
    user = User(
        username=username,
        password_hash=hash_password(password),
        nickname=nickname.strip()[:30] or username,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(Streak(user_id=user.id or 0))
    session.commit()
    return _redirect_with_cookie(user)


@router.post("/account/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(User.username == normalize_username(username))
    ).first()
    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse("/account?error=login", status_code=303)
    return _redirect_with_cookie(user)


@router.post("/account/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
