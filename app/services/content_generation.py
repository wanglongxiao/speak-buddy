import asyncio
import json
from datetime import date

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import get_settings
from app.models import User
from app.models.schemas import (
    PRACTICE_COUNTS,
    DailyPracticePayload,
    DailyReadAloud,
    DailyTopic,
    DifficultyPracticePayload,
)
from app.services.content_bank import fallback_daily_payload
from app.services.prompts import load_prompt
from app.skills.difficulty_skill import profile_for


def _fallback(user: User, variant: int) -> DailyPracticePayload:
    return fallback_daily_payload(date.today(), user.id or 0, variant)


def _level_from_fallback(
    payload: DailyPracticePayload, difficulty: str
) -> DifficultyPracticePayload:
    return DifficultyPracticePayload(
        topics=[
            {"title": item.title, "questions": item.questions}
            for item in payload.topics
            if item.difficulty == difficulty
        ],
        read_aloud=[
            item.text for item in payload.read_aloud if item.difficulty == difficulty
        ],
    )


async def _generate_level(
    client: AsyncOpenAI,
    difficulty: str,
    avoid: dict[str, list[str]],
    nonce: str,
    fallback: DifficultyPracticePayload,
) -> tuple[DifficultyPracticePayload, bool]:
    settings = get_settings()
    profile = profile_for(difficulty)
    topic_count, line_count = PRACTICE_COUNTS[difficulty]
    context = {
        "date": date.today().isoformat(),
        "nonce": f"{nonce}:{difficulty}",
        "difficulty": difficulty,
        "topic_count": topic_count,
        "read_aloud_count": line_count,
        "question_count": [8, 12],
        "target_words": [profile.min_words, profile.max_words],
        "vocabulary": profile.vocabulary,
        "avoid": avoid,
    }
    try:
        response = await client.chat.completions.create(
            model=settings.main_agent_endpoint,
            messages=[
                {"role": "system", "content": load_prompt("daily_content_prompt.md")},
                {"role": "user", "content": json.dumps(context)},
            ],
            response_format={"type": "json_object"},
            temperature=0.9,
            extra_body={"thinking": {"type": "disabled"}},
        )
        payload = DifficultyPracticePayload.model_validate_json(
            response.choices[0].message.content or "{}"
        )
        titles = {item.title.casefold() for item in payload.topics}
        lines = {item.casefold() for item in payload.read_aloud}
        if (
            len(payload.topics) != topic_count
            or len(payload.read_aloud) != line_count
            or len(titles) != topic_count
            or len(lines) != line_count
        ):
            raise ValueError("generated level count is invalid")
        return payload, True
    except (ValidationError, ValueError, IndexError, json.JSONDecodeError, Exception):
        return fallback, False


async def generate_daily_payload(
    user: User,
    nonce: str,
    avoid: dict[str, list[str]],
) -> tuple[DailyPracticePayload, str]:
    settings = get_settings()
    variant = sum(ord(char) for char in nonce)
    fallback = _fallback(user, variant)
    if not settings.ai_enabled:
        return fallback, "fallback"
    client = AsyncOpenAI(
        api_key=settings.modelark_api_key,
        base_url=settings.modelark_base_url,
    )
    levels = list(PRACTICE_COUNTS)
    results = await asyncio.gather(
        *[
            _generate_level(
                client,
                difficulty,
                avoid,
                nonce,
                _level_from_fallback(fallback, difficulty),
            )
            for difficulty in levels
        ]
    )
    topics: list[DailyTopic] = []
    lines: list[DailyReadAloud] = []
    for difficulty, (payload, _) in zip(levels, results):  # noqa: B905 - Python 3.9
        topics.extend(
            DailyTopic(
                title=item.title,
                difficulty=difficulty,
                questions=item.questions,
            )
            for item in payload.topics
        )
        lines.extend(
            DailyReadAloud(difficulty=difficulty, text=text)
            for text in payload.read_aloud
        )
    try:
        combined = DailyPracticePayload(topics=topics, read_aloud=lines)
    except ValidationError:
        return fallback, "fallback"
    provider = "modelark" if all(success for _, success in results) else "mixed"
    return combined, provider
