from datetime import date

from app.models.schemas import (
    PRACTICE_COUNTS,
    DailyPracticePayload,
    DailyReadAloud,
    DailyTopic,
)
from app.services.content_bank_data import READ_ALOUD_BANK, TOPIC_BANK
from app.skills.difficulty_skill import question_for

QUESTION_COUNTS = {"easy": 8, "normal": 9, "hard": 10, "expert": 12}


def _questions(title: str, base: str, difficulty: str) -> list[str]:
    subject = title.lower()
    easy = [
        question_for(title, "easy", base),
        f"When do you usually think about {subject}?",
        f"Who would you like to share {subject} with?",
        f"What is one good thing about {subject}?",
        f"How does {subject} make you feel?",
        f"Where can you enjoy {subject}?",
        f"What would you like to try next about {subject}?",
        f"Can you share a short story about {subject}?",
    ]
    normal = [
        base,
        f"What recent experience changed how you think about {subject}?",
        f"Which part of {subject} do you enjoy most, and why?",
        f"How would you introduce {subject} to a new classmate?",
        f"What challenge can happen with {subject}, and how would you handle it?",
        f"Who has influenced your ideas about {subject}?",
        f"What detail makes {subject} memorable for you?",
        f"How might {subject} be different next year?",
        f"What advice would you give a friend about {subject}?",
    ]
    hard = normal + [
        f"How could people improve {subject} while respecting different needs?"
    ]
    expert = hard + [
        f"Which assumptions about {subject} deserve to be questioned?",
        f"How would you defend your view about {subject} with strong evidence?",
    ]
    options = {
        "easy": easy,
        "normal": normal,
        "hard": hard,
        "expert": expert,
    }[difficulty]
    return options[: QUESTION_COUNTS[difficulty]]


def _level_sentence(sentence: str, difficulty: str) -> str:
    stem = sentence.rstrip(".?")
    if difficulty == "easy":
        return f"Today, {sentence[0].lower() + sentence[1:]}"
    if difficulty == "normal":
        return sentence
    if sentence.endswith("?"):
        suffix = (
            " and give one clear reason?"
            if difficulty == "hard"
            else " and compare two possible responses?"
        )
    else:
        suffix = (
            ", and I can explain why it matters."
            if difficulty == "hard"
            else ", while considering a different point of view."
        )
    return stem + suffix


def fallback_daily_payload(
    content_date: date,
    user_id: int,
    variant: int = 0,
) -> DailyPracticePayload:
    offset = (content_date.toordinal() + user_id * 7 + variant) % len(TOPIC_BANK)
    selected = [
        TOPIC_BANK[(offset + index) % len(TOPIC_BANK)]
        for index in range(len(TOPIC_BANK))
    ]
    topics: list[DailyTopic] = []
    cursor = 0
    for difficulty, (topic_count, _) in PRACTICE_COUNTS.items():
        for title, base in selected[cursor : cursor + topic_count]:
            topics.append(
                DailyTopic(
                    title=title,
                    difficulty=difficulty,
                    questions=_questions(title, base, difficulty),
                )
            )
        cursor += topic_count

    read_offset = (content_date.toordinal() * 3 + user_id + variant) % len(
        READ_ALOUD_BANK
    )
    read_aloud: list[DailyReadAloud] = []
    cursor = 0
    for difficulty, (_, line_count) in PRACTICE_COUNTS.items():
        for index in range(line_count):
            source = READ_ALOUD_BANK[
                (read_offset + cursor + index) % len(READ_ALOUD_BANK)
            ]
            read_aloud.append(
                DailyReadAloud(
                    difficulty=difficulty,
                    text=_level_sentence(source, difficulty),
                )
            )
        cursor += line_count
    return DailyPracticePayload(topics=topics, read_aloud=read_aloud)
