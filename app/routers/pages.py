import json
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_
from sqlmodel import Session, col, select

from app.config import ROOT
from app.db import get_session
from app.models import (
    Badge,
    BadgeAward,
    LoudMeter,
    PracticeSession,
    Streak,
    Topic,
    Turn,
)
from app.services.auth import request_user
from app.services.daily_content import ensure_daily_content, read_aloud_lines
from app.services.i18n import context_for
from app.skills.difficulty_skill import question_for
from app.skills.gamify_skill import title_for

router = APIRouter()
templates = Jinja2Templates(directory=ROOT / "app" / "templates")


def page_context(request: Request, session: Session, page: str) -> dict[str, object]:
    user = request_user(request, session)
    loud = session.exec(
        select(LoudMeter).where(
            LoudMeter.user_id == user.id, LoudMeter.date == date.today()
        )
    ).first()
    return {
        **context_for(request),
        "page": page,
        "user": user,
        "loud_seconds": loud.total_seconds if loud else 0,
        "daily_read_aloud": [],
    }


@router.get("/")
async def home(request: Request, session: Session = Depends(get_session)):
    context = page_context(request, session, "home")
    user = context["user"]
    daily = await ensure_daily_content(session, user)
    first_topic = session.exec(
        select(Topic).where(Topic.daily_content_id == daily.id).order_by(col(Topic.id))
    ).first()
    streak = session.get(Streak, user.id) or Streak(user_id=user.id or 0)
    context.update(
        {
            "title": title_for(user.total_xp),
            "streak": streak,
            "first_topic_id": first_topic.id if first_topic else 1,
            "daily_content": daily,
        }
    )
    return templates.TemplateResponse(request, "home.html", context)


@router.get("/warmup")
async def warmup(
    request: Request,
    topic_id: int = 1,
    session: Session = Depends(get_session),
):
    if "quest" in request.query_params:
        return RedirectResponse(f"/practice?topic_id={topic_id}", status_code=303)
    context = page_context(request, session, "warmup")
    daily = await ensure_daily_content(session, context["user"])
    context.update(
        {
            "daily_read_aloud": read_aloud_lines(daily),
            "topic_id": topic_id,
        }
    )
    return templates.TemplateResponse(request, "warmup.html", context)


@router.get("/practice")
def practice(
    request: Request,
    topic_id: int = 1,
    session: Session = Depends(get_session),
):
    context = page_context(request, session, "practice")
    user = context["user"]
    topic = session.exec(
        select(Topic).where(
            Topic.id == topic_id,
            or_(Topic.is_system.is_(True), Topic.owner_user_id == user.id),
        )
    ).first()
    topic = (
        topic or session.exec(select(Topic).where(Topic.is_system.is_(True))).first()
    )
    context["topic"] = topic
    starter_question = (
        topic.starter_question
        if topic.daily_content_id
        else question_for(topic.title, user.default_difficulty, topic.starter_question)
    )
    questions = [starter_question]
    if topic.daily_content_id:
        try:
            stored = json.loads(topic.follow_up_hints_json)
            questions = [str(item) for item in stored] or questions
        except (TypeError, json.JSONDecodeError):
            pass
    context["starter_question"] = starter_question
    context["topic_questions"] = questions
    return templates.TemplateResponse(request, "practice.html", context)


@router.get("/topics")
async def topics(request: Request, session: Session = Depends(get_session)):
    context = page_context(request, session, "topics")
    user = context["user"]
    daily = await ensure_daily_content(session, user)
    topics = session.exec(
        select(Topic)
        .where(
            or_(
                Topic.daily_content_id == daily.id,
                and_(
                    Topic.owner_user_id == user.id,
                    Topic.daily_content_id.is_(None),
                ),
            )
        )
        .order_by(col(Topic.id))
    ).all()
    context["topics"] = [
        {
            "id": topic.id,
            "title": topic.title,
            "difficulty": user.default_difficulty,
            "starter_question": (
                topic.starter_question
                if topic.daily_content_id
                else question_for(
                    topic.title,
                    user.default_difficulty,
                    topic.starter_question,
                )
            ),
        }
        for topic in topics
    ]
    update_status = request.query_params.get("updated")
    context["content_updated"] = update_status == "1"
    context["content_pending"] = update_status == "pending"
    return templates.TemplateResponse(request, "topics.html", context)


@router.get("/history")
def history(request: Request, session: Session = Depends(get_session)):
    context = page_context(request, session, "history")
    user = context["user"]
    context["turns"] = session.exec(
        select(Turn)
        .join(PracticeSession)
        .where(PracticeSession.user_id == user.id)
        .order_by(col(Turn.created_at).desc())
        .limit(30)
    ).all()
    return templates.TemplateResponse(request, "history.html", context)


@router.get("/trophy")
def trophy(request: Request, session: Session = Depends(get_session)):
    context = page_context(request, session, "trophy")
    user = context["user"]
    context["badges"] = session.exec(select(Badge)).all()
    context["earned"] = {
        award.badge_code
        for award in session.exec(
            select(BadgeAward).where(BadgeAward.user_id == user.id)
        ).all()
    }
    return templates.TemplateResponse(request, "trophy.html", context)
