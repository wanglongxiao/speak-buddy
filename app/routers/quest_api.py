from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, col, select

from app.compat import UTC
from app.db import get_session
from app.models import PracticeSession, Turn
from app.models.schemas import QuestRequest
from app.routers.api import award_badges, current_user
from app.services.concurrency import serialized_write
from app.services.evaluation import evaluate_topic_turns, save_evaluation
from app.skills.gamify_skill import evaluate

router = APIRouter(prefix="/api")


def _active_session(
    session: Session, user_id: int, topic_id: int | None, conversation_id: str = ""
) -> PracticeSession | None:
    statement = select(PracticeSession).where(
        PracticeSession.user_id == user_id,
        PracticeSession.finished_at.is_(None),
        PracticeSession.conversation_id == conversation_id,
    )
    if topic_id is not None:
        statement = statement.where(PracticeSession.topic_id == topic_id)
    return session.exec(
        statement.order_by(col(PracticeSession.started_at).desc())
    ).first()


@router.post("/quest/complete")
@serialized_write
def quest_complete(
    request: Request,
    payload: QuestRequest,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    active = _active_session(
        session, user.id or 0, payload.topic_id, payload.conversation_id
    )
    if not active:
        return {
            **asdict(evaluate("none", {"total_xp": user.total_xp})),
            "evaluation": None,
        }
    turns = session.exec(
        select(Turn).where(Turn.session_id == active.id).order_by(col(Turn.created_at))
    ).all()
    evaluation = evaluate_topic_turns(turns)
    save_evaluation(
        session,
        user.id or 0,
        "topic",
        "\n".join(turn.question for turn in turns),
        "\n".join(turn.transcript for turn in turns),
        evaluation,
        active.id,
    )
    reward = evaluate(
        "quest_complete",
        {
            "total_xp": user.total_xp,
            "challenge": active.difficulty in {"hard", "expert"},
        },
    )
    active.finished_at = datetime.now(UTC)
    active.total_xp += reward.xp
    user.total_xp += reward.xp
    award_badges(session, user.id or 0, reward.badges)
    session.add(active)
    session.add(user)
    session.commit()
    return {**asdict(reward), "evaluation": evaluation.model_dump()}


@router.post("/quest/end")
@serialized_write
def quest_end(
    request: Request,
    payload: QuestRequest,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    active = _active_session(
        session,
        user.id or 0,
        payload.topic_id,
        payload.conversation_id,
    )
    if active:
        active.finished_at = datetime.now(UTC)
        session.add(active)
        session.commit()
    return {"ended": active is not None}
