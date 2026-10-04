import asyncio
import json
from dataclasses import asdict
from datetime import date, datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlmodel import Session, col, select

from app.compat import UTC
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
from app.services.voices import DEFAULT_BUDDY_VOICE, valid_buddy_voice
from app.skills.asr_skill import transcribe
from app.skills.asr_skill.streaming import SeedASRStream
from app.skills.coach_skill import coach
from app.skills.gamify_skill import evaluate
from app.skills.loud_skill import assess
from app.skills.pronunciation_skill import grade
from app.skills.tos_skill import resolve_audio, store_audio
from app.skills.tts_skill import stream_speech, synthesize

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


@router.websocket("/asr/stream")
async def asr_stream(
    websocket: WebSocket,
    session: Session = Depends(get_session),
):
    request_user(websocket, session)
    await websocket.accept()
    if not get_settings().speech_enabled:
        await websocket.send_json(
            {"type": "unavailable", "detail": "Streaming ASR is not configured"}
        )
        await websocket.close(code=1013)
        return

    provider = SeedASRStream()
    try:
        await provider.connect()
        await websocket.send_json({"type": "ready"})

        async def send_audio() -> None:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    raise WebSocketDisconnect(message.get("code", 1000))
                audio = message.get("bytes")
                if audio:
                    if len(audio) > 65_536:
                        raise ValueError("Audio chunk is too large")
                    await provider.send_audio(audio)
                    continue
                if message.get("text"):
                    command = json.loads(message["text"])
                    if command.get("type") == "stop":
                        await provider.finish()
                        return

        async def send_results() -> None:
            while True:
                result = await provider.receive()
                if result.error:
                    await websocket.send_json({"type": "error", "detail": result.error})
                    return
                if result.text:
                    await websocket.send_json(
                        {
                            "type": "transcript",
                            "text": result.text,
                            "final": result.final,
                        }
                    )
                if result.final:
                    return

        audio_task = asyncio.create_task(send_audio())
        result_task = asyncio.create_task(send_results())
        done, _ = await asyncio.wait(
            {audio_task, result_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if audio_task in done and not result_task.done():
            await asyncio.wait_for(result_task, timeout=6)
        if result_task in done and not audio_task.done():
            audio_task.cancel()
        await websocket.close()
    except (OSError, RuntimeError, ValueError, WebSocketDisconnect, TimeoutError):
        try:
            await websocket.send_json(
                {"type": "unavailable", "detail": "Streaming ASR unavailable"}
            )
            await websocket.close(code=1011)
        except RuntimeError:
            pass
    finally:
        await provider.close()


def user_voice(user: User) -> str:
    return (
        user.buddy_voice if valid_buddy_voice(user.buddy_voice) else DEFAULT_BUDDY_VOICE
    )


@router.post("/tts")
async def tts(
    payload: TTSRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    voice = payload.voice or user_voice(user)
    if not valid_buddy_voice(voice):
        raise HTTPException(status_code=422, detail="Unsupported Buddy voice")
    return {"url": await synthesize(payload.text, payload.speed, voice)}


@router.get("/tts/stream")
async def tts_stream(
    request: Request,
    text: str = Query(min_length=1, max_length=500),
    speed: str = Query(default="normal", pattern="^(slow|normal|fast)$"),
    voice: str = "",
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    selected = voice or user_voice(user)
    if not valid_buddy_voice(selected):
        raise HTTPException(status_code=422, detail="Unsupported Buddy voice")
    return StreamingResponse(
        stream_speech(text, speed, selected),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store"},
    )


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
