from __future__ import annotations

import json

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import get_settings
from app.models.schemas import CoachResult, ScoreSet
from app.services.prompts import load_prompt
from app.skills.difficulty_skill import normalize, profile_for


def fallback_coach(
    transcript: str,
    confidence: float = 0.8,
    difficulty: str = "normal",
    question: str = "",
) -> CoachResult:
    words = transcript.split()
    quote = " ".join(words[:4]) or "your brave voice"
    xp = min(30, 10 + (5 if len(words) >= 8 else 0) + (5 if len(words) >= 15 else 0))
    level = normalize(difficulty)
    profile = profile_for(level)
    response_length = min(100, round(len(words) / profile.min_words * 100))
    confidence_score = max(0, min(100, round((confidence - 0.35) / 0.65 * 100)))
    fluency = round(confidence_score * 0.65 + response_length * 0.35)
    question_words = {
        word.lower().strip("?!.,")
        for word in question.split()
        if len(word.strip("?!.,")) > 3
    }
    spoken_words = {word.lower().strip("?!.,") for word in words}
    overlap = len(question_words & spoken_words)
    relevance = min(90, 45 + overlap * 15)
    word_accuracy = min(90, round(55 + confidence * 35))
    rubric = [
        confidence_score,
        fluency,
        response_length,
        word_accuracy,
        relevance,
    ]
    overall = round(sum(rubric) / len(rubric) * 0.96)
    if len(words) < profile.min_words:
        overall = min(overall, 75)
    follow_up = {
        "easy": "What was your favorite part?",
        "normal": "What part would you love to experience again?",
        "hard": "Why did that experience matter to you personally?",
        "expert": "How might someone with a different view respond to your idea?",
    }[level]
    new_words = {
        "easy": ["favorite", "exciting", "proud"],
        "normal": ["memorable", "enthusiastic", "confident"],
        "hard": ["meaningful", "perspective", "challenging"],
        "expert": ["significant", "alternative", "convincing"],
    }[level]
    return CoachResult(
        praise=f'I loved hearing "{quote}" - that sounded clear and thoughtful!',
        tiny_tweak="You could also say, 'I really enjoyed it because...'",
        highlight_words=["really", "because"],
        ideal_rephrase=(
            "I really enjoyed it because it made the whole day feel special."
        ),
        follow_up_question=follow_up,
        scores=ScoreSet(
            pronunciation=confidence_score,
            fluency=fluency,
            vocabulary=word_accuracy,
            confidence=confidence_score,
            response_length=response_length,
            word_accuracy=word_accuracy,
            relevance=relevance,
        ),
        overall_score=overall,
        brief_feedback=(
            "Your idea was clear and connected. Add one more detail to make "
            "your answer even stronger."
        ),
        xp_earned=max(10, xp),
        encourage_loud=len(words) < 8 or confidence < 0.6,
        emotion_boost="Your idea has real personality - keep that voice going!",
        suggested_new_words=new_words,
    )


async def coach(
    question: str,
    transcript: str,
    confidence: float,
    history: list[dict[str, str]] | None = None,
    difficulty: str = "normal",
) -> CoachResult:
    settings = get_settings()
    if not settings.ai_enabled:
        return fallback_coach(transcript, confidence, difficulty, question)
    profile = profile_for(difficulty)
    context = {
        "question": question,
        "transcript": transcript,
        "asr_confidence": confidence,
        "history": history or [],
        "difficulty": profile.code,
        "target_words": [profile.min_words, profile.max_words],
        "vocabulary": profile.vocabulary,
    }
    client = AsyncOpenAI(
        api_key=settings.modelark_api_key,
        base_url=settings.modelark_base_url,
    )
    try:
        response = await client.chat.completions.create(
            model=settings.main_agent_endpoint,
            messages=[
                {"role": "system", "content": load_prompt("coach_prompt.md")},
                {"role": "user", "content": json.dumps(context)},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            extra_body={"thinking": {"type": "disabled"}},
        )
        content = response.choices[0].message.content or "{}"
        return CoachResult.model_validate_json(content)
    except (ValidationError, json.JSONDecodeError, IndexError, Exception):
        return fallback_coach(transcript, confidence, difficulty, question)
