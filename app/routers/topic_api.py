import json

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.db import get_session
from app.models import Topic
from app.routers.api import award_badges, current_user
from app.skills.topic_skill import create_topic, match_voice_command

router = APIRouter(prefix="/api")


@router.post("/topics/create-from-voice")
async def topic_from_voice(
    payload: dict[str, str],
    request: Request,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    card = await create_topic(payload.get("raw_text", ""), user.default_difficulty)
    topic = Topic(
        owner_user_id=user.id,
        title=card.title,
        difficulty=card.difficulty,
        starter_question=card.starter_question,
        follow_up_hints_json=json.dumps(card.follow_up_hints),
        ideal_answer=card.ideal_answer_sample,
        suggested_words_json=json.dumps(card.suggested_new_words),
        is_system=False,
    )
    session.add(topic)
    session.commit()
    session.refresh(topic)
    award_badges(session, user.id or 1, ["topic-creator"])
    session.commit()
    return {**card.model_dump(), "id": topic.id}


@router.post("/voice-command")
def voice_command(payload: dict[str, str]):
    intent, slots = match_voice_command(payload.get("transcript", ""))
    return {"intent": intent, "slots": slots}
