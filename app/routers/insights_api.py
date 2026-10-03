from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.db import get_session
from app.models import Badge, BadgeAward
from app.services.auth import request_user
from app.services.i18n import language_for
from app.services.progress import build_progress

router = APIRouter(prefix="/api")


@router.get("/progress")
def progress(
    request: Request,
    period: str = "week",
    session: Session = Depends(get_session),
):
    user = request_user(request, session)
    return build_progress(session, user, period, language_for(request))


@router.get("/trophies")
def trophies(request: Request, session: Session = Depends(get_session)):
    user = request_user(request, session)
    earned_codes = {
        item.badge_code
        for item in session.exec(
            select(BadgeAward).where(BadgeAward.user_id == user.id)
        )
    }
    badges = session.exec(select(Badge)).all()
    return {
        "earned": [item for item in badges if item.code in earned_codes],
        "locked": [item for item in badges if item.code not in earned_codes],
    }
