import json
from dataclasses import asdict
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, col, select

from app.config import get_settings
from app.db import get_session
from app.models import (
    BadgeAward,
    LoudMeter,
    PracticeSession,
    Topic,
    Turn,
    User,
)
from app.models.schemas import (
    ASRRequest,
    CoachRequest,
    LoudRecordRequest,
    PronunciationRequest,
    TTSRequest,
)
from app.services.auth import request_user
from app.skills.asr_skill import transcribe
from app.skills.coach_skill import coach
from app.skills.gamify_skill import evaluate
from app.skills.loud_skill import assess
from app.skills.pronunciation_skill import grade
from app.skills.tos_skill import resolve_audio, store_audio
from app.skills.tts_skill import synthesize

router = APIRouter(prefix="/api")


def current_user(request: Request, session: Session) -> User:
    return request_user(request, session)


def audio_url(key: str) -> str:
    local = resolve_audio(key)
    if local:
        return local.url
    settings = get_settings()
    host = settings.tos_endpoint.removeprefix("https://").rstrip("/")
    return f"https://{settings.tos_bucket}.{host}/{key}"


def award_badges(session: Session, user_id: int, codes: list[str]) -> None:
    for code in codes:
        exists = session.exec(
            select(BadgeAward).where(
                BadgeAward.user_id == user_id, BadgeAward.badge_code == code
            )
        ).first()
        if not exists:
            session.add(BadgeAward(user_id=user_id, badge_code=code))


@router.post("/upload-audio")
async def upload_audio(
    audio: UploadFile = File(...),
    rms: float = Form(0),
    duration_ms: int = Form(0),
):
    content = await audio.read()
    stored = await run_in_threadpool(
        store_audio,
        content,
        audio.filename or "recording.webm",
        audio.content_type or "audio/webm",
    )
    loud = await run_in_threadpool(
        assess,
        rms,
        duration_ms,
        wav_path=stored.local_path,
    )
    return {
        "audio_key": stored.key,
        "url": stored.url,
        "rms": loud.rms,
        "duration_ms": loud.duration_ms,
        "provider": stored.provider,
    }


@router.post("/asr")
async def asr(payload: ASRRequest):
    result = await transcribe(audio_url(payload.audio_key))
    return asdict(result)


@router.post("/tts")
async def tts(payload: TTSRequest):
    return {"url": await synthesize(payload.text, payload.speed, payload.voice)}


@router.post("/coach")
async def coach_turn(
    payload: CoachRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    topic = session.get(Topic, payload.topic_id)
    if not topic or not (topic.is_system or topic.owner_user_id == user.id):
        raise HTTPException(status_code=404, detail="Topic not found")
    result = await coach(
        payload.question,
        payload.transcript,
        payload.asr_confidence,
        payload.history,
        user.default_difficulty,
    )
    unfinished = session.exec(
        select(PracticeSession)
        .where(
            PracticeSession.user_id == user.id,
            PracticeSession.finished_at.is_(None),
        )
        .order_by(col(PracticeSession.started_at).desc())
    ).all()
    active = next((item for item in unfinished if item.topic_id == topic.id), None)
    for practice in unfinished:
        if practice is not active:
            practice.finished_at = datetime.now(UTC)
            session.add(practice)
    if not active:
        active = PracticeSession(
            user_id=user.id or 1,
            topic_id=topic.id,
            difficulty=user.default_difficulty,
            speed=user.default_speed,
        )
        session.add(active)
        session.commit()
        session.refresh(active)
    reward = evaluate("turn", {"total_xp": user.total_xp, "coach_xp": result.xp_earned})
    user.total_xp += reward.xp
    active.total_xp += reward.xp
    turn = Turn(
        session_id=active.id or 1,
        topic_id=topic.id or 1,
        question=payload.question,
        transcript=payload.transcript,
        confidence=payload.asr_confidence,
        coach_json=result.model_dump_json(),
        scores_json=json.dumps(result.scores.model_dump()),
        xp=reward.xp,
    )
    session.add(turn)
    session.flush()
    session.add(user)
    session.add(active)
    session.commit()
    return result


@router.post("/pronunciation")
def pronunciation(payload: PronunciationRequest):
    return asdict(grade(payload.reference_text, payload.hypothesis, payload.confidence))


@router.post("/loud/record")
def record_loud(
    payload: LoudRecordRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    result = assess(payload.rms, payload.duration_ms)
    user = current_user(request, session)
    meter = session.exec(
        select(LoudMeter).where(
            LoudMeter.user_id == user.id, LoudMeter.date == date.today()
        )
    ).first()
    if not meter:
        meter = LoudMeter(user_id=user.id or 1)
    meter.total_seconds += result.counted_seconds
    if payload.context == "warmup":
        meter.warmup_count += 1
    if payload.context == "shoutout":
        meter.shoutout_count += 1
    reward = evaluate(
        "shoutout",
        {
            "count": meter.shoutout_count,
            "loud_seconds": meter.total_seconds,
            "total_xp": user.total_xp,
        },
    )
    user.total_xp += reward.xp
    award_badges(session, user.id or 1, reward.badges)
    session.add(meter)
    session.add(user)
    session.commit()
    return {**asdict(result), "total_seconds": meter.total_seconds}
