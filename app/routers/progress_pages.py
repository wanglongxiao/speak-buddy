from __future__ import annotations

import base64
import io
from datetime import date

import qrcode
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.config import ROOT, get_settings
from app.db import get_session
from app.models import LoudMeter, User
from app.routers.pages import page_context
from app.services.auth import parent_share_user, signed_token
from app.services.progress import build_progress

router = APIRouter()
templates = Jinja2Templates(directory=ROOT / "app" / "templates")


def progress_context(
    request: Request, session: Session, user: User | None = None
) -> dict[str, object]:
    context = page_context(request, session, "progress")
    selected_user = user or context["user"]
    if user:
        context["user"] = user
        loud = session.exec(
            select(LoudMeter).where(
                LoudMeter.user_id == user.id, LoudMeter.date == date.today()
            )
        ).first()
        context["loud_seconds"] = loud.total_seconds if loud else 0
    context.update(
        build_progress(
            session,
            selected_user,
            request.query_params.get("period", "week"),
            context["lang"],
        )
    )
    return context


@router.get("/progress")
def progress(request: Request, session: Session = Depends(get_session)):
    context = progress_context(request, session)
    return templates.TemplateResponse(request, "progress.html", context)


@router.get("/progress/parent")
def parent(request: Request, session: Session = Depends(get_session)):
    shared_user = parent_share_user(request.query_params.get("share"), session)
    context = progress_context(request, session, shared_user)
    share = signed_token("parent", context["user"].id or 0)
    share_url = f"{get_settings().app_base_url}/progress/parent?share={share}"
    qr = qrcode.make(share_url)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    context.update(
        {
            "qr_data": "data:image/png;base64,"
            + base64.b64encode(buffer.getvalue()).decode(),
            "highlight": context["t"]["parent_highlight"],
            "share_token": share,
        }
    )
    return templates.TemplateResponse(request, "parent.html", context)
