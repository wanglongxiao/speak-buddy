from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.config import ROOT
from app.db import get_session
from app.routers.pages import page_context
from app.services.auth import request_user
from app.services.voices import BUDDY_VOICES, valid_buddy_voice

router = APIRouter()
templates = Jinja2Templates(directory=ROOT / "app" / "templates")


@router.get("/settings")
def settings_page(request: Request, session: Session = Depends(get_session)):
    context = page_context(request, session, "settings")
    context["buddy_voices"] = BUDDY_VOICES
    return templates.TemplateResponse(request, "settings.html", context)


@router.post("/settings")
def save_settings(
    request: Request,
    nickname: str = Form(...),
    lang: str = Form(...),
    difficulty: str = Form(...),
    speed: str = Form(...),
    buddy_voice: str | None = Form(None),
    session: Session = Depends(get_session),
):
    user = request_user(request, session)
    user.nickname = nickname[:30]
    user.lang = lang if lang in {"en", "zh"} else "en"
    user.default_difficulty = (
        difficulty if difficulty in {"easy", "normal", "hard", "expert"} else "normal"
    )
    user.default_speed = speed if speed in {"slow", "normal", "fast"} else "normal"
    if buddy_voice and valid_buddy_voice(buddy_voice):
        user.buddy_voice = buddy_voice
    session.add(user)
    session.commit()
    response = RedirectResponse("/settings", status_code=303)
    response.set_cookie("lang", user.lang, max_age=31_536_000, samesite="lax")
    return response


@router.get("/language/{lang}")
def set_language(lang: str, request: Request):
    target = request.headers.get("referer", "/")
    response = RedirectResponse(target, status_code=303)
    response.set_cookie("lang", lang if lang in {"en", "zh"} else "en")
    return response
