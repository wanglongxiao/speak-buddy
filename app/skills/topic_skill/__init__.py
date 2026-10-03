from openai import AsyncOpenAI

from app.config import get_settings
from app.models.schemas import TopicCard
from app.services.prompts import load_prompt
from app.skills.difficulty_skill import normalize, question_for


def fallback_topic(raw_text: str, difficulty: str = "normal") -> TopicCard:
    subject = raw_text.strip()[:45] or "Something I Love"
    level = normalize(difficulty)
    words = {
        "easy": ["fun", "favorite", "practice"],
        "normal": ["interesting", "experience", "recommend"],
        "hard": ["memorable", "challenging", "perspective"],
        "expert": ["significant", "influence", "alternative"],
    }[level]
    return TopicCard(
        title=subject.title(),
        difficulty=level,
        starter_question=question_for(subject, level),
        follow_up_hints=[
            "How did you discover it?",
            "How does it make you feel?",
            "Who would enjoy it with you?",
            "What happened recently?",
            "What would you try next?",
        ],
        ideal_answer_sample=f"I enjoy {subject} because it gives me new ideas.",
        suggested_new_words=words,
    )


async def create_topic(raw_text: str, difficulty: str = "normal") -> TopicCard:
    level = normalize(difficulty)
    settings = get_settings()
    if not settings.ai_enabled:
        return fallback_topic(raw_text, level)
    client = AsyncOpenAI(
        api_key=settings.modelark_api_key,
        base_url=settings.modelark_base_url,
    )
    try:
        response = await client.chat.completions.create(
            model=settings.main_agent_endpoint,
            messages=[
                {"role": "system", "content": "Return strict JSON only."},
                {
                    "role": "user",
                    "content": load_prompt("topic_prompt.md")
                    .replace("{{raw_text}}", raw_text)
                    .replace("{{difficulty}}", level),
                },
            ],
            response_format={"type": "json_object"},
            extra_body={"thinking": {"type": "disabled"}},
        )
        return TopicCard.model_validate_json(
            response.choices[0].message.content or "{}"
        )
    except Exception:
        return fallback_topic(raw_text, level)


def match_voice_command(transcript: str) -> tuple[str, dict[str, str]]:
    text = transcript.lower().strip()
    if "let's go" in text or "lets go" in text:
        return "start_quest", {}
    if "new topic" in text:
        return "create_topic", {}
    for level in ("easy", "normal", "hard", "expert"):
        if level in text:
            return "set_difficulty", {"difficulty": level}
    if "let's start" in text or "lets start" in text:
        return "start_topic", {}
    return "unknown", {}
