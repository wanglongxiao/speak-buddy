import asyncio
import json
from datetime import UTC, date, datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.models import (
    DailyPracticeContent,
    PracticeSession,
    Topic,
    Turn,
    User,
)
from app.services.content_releases import (
    cleanup_expired_releases,
    create_release,
    latest_release,
    payload_for_release,
)

_CONTENT_LOCKS: dict[tuple[asyncio.AbstractEventLoop, int], asyncio.Lock] = {}


def current_daily_content(
    session: Session, user_id: int, content_date: date | None = None
) -> DailyPracticeContent | None:
    return session.exec(
        select(DailyPracticeContent).where(
            DailyPracticeContent.user_id == user_id,
            DailyPracticeContent.content_date == (content_date or date.today()),
        )
    ).first()


def _remove_batch(session: Session, batch: DailyPracticeContent) -> None:
    topics = session.exec(select(Topic).where(Topic.daily_content_id == batch.id)).all()
    topic_ids = [topic.id for topic in topics if topic.id is not None]
    if topic_ids:
        fallback = session.exec(
            select(Topic).where(
                Topic.daily_content_id.is_(None),
                Topic.is_system.is_(True),
            )
        ).first()
        sessions = session.exec(
            select(PracticeSession).where(col(PracticeSession.topic_id).in_(topic_ids))
        ).all()
        turns = session.exec(
            select(Turn).where(col(Turn.topic_id).in_(topic_ids))
        ).all()
        for practice in sessions:
            practice.topic_id = None
            session.add(practice)
        for turn in turns:
            turn.topic_id = fallback.id if fallback else topic_ids[0]
            session.add(turn)
        for topic in topics:
            session.delete(topic)
    session.delete(batch)


def _batch_in_use(session: Session, batch: DailyPracticeContent) -> bool:
    topic_ids = [
        topic.id
        for topic in session.exec(
            select(Topic).where(Topic.daily_content_id == batch.id)
        ).all()
        if topic.id is not None
    ]
    if not topic_ids:
        return False
    return (
        session.exec(
            select(PracticeSession).where(
                col(PracticeSession.topic_id).in_(topic_ids),
                PracticeSession.finished_at.is_(None),
            )
        ).first()
        is not None
    )


def cleanup_expired_content(session: Session, now: datetime | None = None) -> int:
    moment = now or datetime.now(UTC)
    expired = session.exec(
        select(DailyPracticeContent).where(DailyPracticeContent.expires_at <= moment)
    ).all()
    removed = 0
    for batch in expired:
        if _batch_in_use(session, batch):
            continue
        _remove_batch(session, batch)
        removed += 1
    if removed:
        session.commit()
    cleanup_expired_releases(session, moment)
    return removed


def read_aloud_lines(batch: DailyPracticeContent | None) -> list[str]:
    if not batch:
        return []
    try:
        values = json.loads(batch.read_aloud_json)
        return [str(value) for value in values]
    except (TypeError, json.JSONDecodeError):
        return []


async def _ensure_daily_content_locked(
    session: Session, user: User, force: bool = False
) -> DailyPracticeContent:
    cleanup_expired_content(session)
    existing = current_daily_content(session, user.id or 0)
    release = latest_release(session, user.default_difficulty)
    if force or not release:
        release = await create_release(session, user)
    if existing and existing.source_release_id == release.id:
        return existing
    if existing and _batch_in_use(session, existing):
        return existing
    payload = payload_for_release(release)
    topics = [
        item for item in payload.topics if item.difficulty == user.default_difficulty
    ]
    lines = [
        item.text
        for item in payload.read_aloud
        if item.difficulty == user.default_difficulty
    ]
    if existing:
        _remove_batch(session, existing)
        session.flush()
    batch = DailyPracticeContent(
        user_id=user.id or 0,
        source_release_id=release.id,
        content_date=date.today(),
        difficulty=user.default_difficulty,
        read_aloud_json=json.dumps(lines),
        generation_provider=release.generation_provider,
        expires_at=release.expires_at,
    )
    try:
        session.add(batch)
        session.flush()
        for card in topics:
            session.add(
                Topic(
                    owner_user_id=user.id,
                    daily_content_id=batch.id,
                    title=card.title,
                    difficulty=user.default_difficulty,
                    starter_question=card.questions[0],
                    follow_up_hints_json=json.dumps(card.questions),
                    is_system=False,
                )
            )
        session.commit()
    except IntegrityError:
        session.rollback()
        winner = current_daily_content(session, user.id or 0)
        if winner:
            return winner
        raise
    session.refresh(batch)
    return batch


async def ensure_daily_content(
    session: Session, user: User, force: bool = False
) -> DailyPracticeContent:
    key = (asyncio.get_running_loop(), user.id or 0)
    lock = _CONTENT_LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        return await _ensure_daily_content_locked(session, user, force)
