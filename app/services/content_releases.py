import json
from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, col, select

from app.models import DailyPracticeContent, PracticeContentRelease, User
from app.models.schemas import DailyPracticePayload
from app.services.content_generation import generate_daily_payload


def payload_for_release(release: PracticeContentRelease) -> DailyPracticePayload:
    return DailyPracticePayload.model_validate(
        {
            "topics": json.loads(release.topics_json),
            "read_aloud": json.loads(release.read_aloud_json),
        }
    )


def latest_release(
    session: Session,
    _difficulty: str,
    content_date: date | None = None,
) -> PracticeContentRelease | None:
    return session.exec(
        select(PracticeContentRelease)
        .where(
            PracticeContentRelease.difficulty == "all",
            PracticeContentRelease.content_date == (content_date or date.today()),
            PracticeContentRelease.expires_at > datetime.now(UTC),
        )
        .order_by(
            col(PracticeContentRelease.created_at).desc(),
            col(PracticeContentRelease.id).desc(),
        )
    ).first()


def _recent_exclusions(session: Session) -> dict[str, list[str]]:
    cutoff = date.today() - timedelta(days=7)
    releases = session.exec(
        select(PracticeContentRelease).where(
            PracticeContentRelease.difficulty == "all",
            PracticeContentRelease.content_date >= cutoff,
        )
    ).all()
    titles: list[str] = []
    sentences: list[str] = []
    for release in releases:
        try:
            payload = payload_for_release(release)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        titles.extend(topic.title for topic in payload.topics)
        sentences.extend(item.text for item in payload.read_aloud)
    return {"titles": titles[-350:], "sentences": sentences[-700:]}


async def _generate_payload(
    session: Session, user: User, nonce: str
) -> tuple[DailyPracticePayload, str]:
    return await generate_daily_payload(user, nonce, _recent_exclusions(session))


async def create_release(session: Session, user: User) -> PracticeContentRelease:
    payload, provider = await _generate_payload(
        session, user, datetime.now(UTC).isoformat()
    )
    release = PracticeContentRelease(
        created_by_user_id=user.id or 0,
        content_date=date.today(),
        difficulty="all",
        topics_json=json.dumps([topic.model_dump() for topic in payload.topics]),
        read_aloud_json=json.dumps([item.model_dump() for item in payload.read_aloud]),
        generation_provider=provider,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(release)
    session.commit()
    session.refresh(release)
    return release


def cleanup_expired_releases(session: Session, now: datetime | None = None) -> int:
    moment = now or datetime.now(UTC)
    expired = session.exec(
        select(PracticeContentRelease).where(
            PracticeContentRelease.expires_at <= moment
        )
    ).all()
    removed = 0
    for release in expired:
        used = session.exec(
            select(DailyPracticeContent).where(
                DailyPracticeContent.source_release_id == release.id
            )
        ).first()
        if not used:
            session.delete(release)
            removed += 1
    if removed:
        session.commit()
    return removed
