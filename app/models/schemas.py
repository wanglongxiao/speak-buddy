from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PRACTICE_COUNTS = {
    "easy": (15, 30),
    "normal": (15, 30),
    "hard": (10, 20),
    "expert": (10, 20),
}


class ScoreSet(BaseModel):
    pronunciation: int = Field(ge=0, le=100)
    fluency: int = Field(ge=0, le=100)
    vocabulary: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    response_length: int = Field(ge=0, le=100)
    word_accuracy: int = Field(ge=0, le=100)
    relevance: int = Field(ge=0, le=100)


class CoachResult(BaseModel):
    praise: str
    tiny_tweak: str | None = Field(default=None, max_length=180)
    highlight_words: list[str] = Field(default_factory=list, max_length=4)
    ideal_rephrase: str
    ideal_rephrase_phonetic_hint: str | None = None
    follow_up_question: str
    scores: ScoreSet
    overall_score: int = Field(ge=0, le=100)
    brief_feedback: str = Field(max_length=180)
    xp_earned: int = Field(ge=10, le=30)
    encourage_loud: bool
    emotion_boost: str = Field(max_length=100)
    suggested_new_words: list[str] = Field(min_length=1, max_length=3)

    @field_validator("ideal_rephrase")
    @classmethod
    def one_breath(cls, value: str) -> str:
        if len(value.split()) > 20:
            raise ValueError("ideal_rephrase must contain at most 20 words")
        return value

    @field_validator("tiny_tweak")
    @classmethod
    def one_tiny_tweak(cls, value: str | None) -> str | None:
        if value and len(value.split()) > 25:
            raise ValueError("tiny_tweak must contain at most 25 words")
        return value


class TopicCard(BaseModel):
    title: str
    difficulty: Literal["easy", "normal", "hard", "expert"]
    starter_question: str
    follow_up_hints: list[str] = Field(min_length=3, max_length=5)
    ideal_answer_sample: str
    suggested_new_words: list[str] = Field(min_length=3, max_length=5)


class GeneratedDailyTopic(BaseModel):
    title: str = Field(min_length=3, max_length=60)
    questions: list[str] = Field(min_length=8, max_length=12)


class DifficultyPracticePayload(BaseModel):
    topics: list[GeneratedDailyTopic] = Field(min_length=10, max_length=15)
    read_aloud: list[str] = Field(min_length=20, max_length=30)


class DailyTopic(GeneratedDailyTopic):
    difficulty: Literal["easy", "normal", "hard", "expert"]


class DailyReadAloud(BaseModel):
    difficulty: Literal["easy", "normal", "hard", "expert"]
    text: str = Field(min_length=8, max_length=300)


class DailyPracticePayload(BaseModel):
    topics: list[DailyTopic] = Field(min_length=50, max_length=50)
    read_aloud: list[DailyReadAloud] = Field(min_length=100, max_length=100)

    @model_validator(mode="after")
    def exact_counts_and_unique_content(self):
        for difficulty, (topic_count, line_count) in PRACTICE_COUNTS.items():
            topics = [item for item in self.topics if item.difficulty == difficulty]
            lines = [item for item in self.read_aloud if item.difficulty == difficulty]
            if len(topics) != topic_count or len(lines) != line_count:
                raise ValueError(f"invalid content count for {difficulty}")
            titles = [item.title.casefold() for item in topics]
            sentences = [item.text.casefold() for item in lines]
            if len(set(titles)) != len(titles) or len(set(sentences)) != len(sentences):
                raise ValueError(f"{difficulty} content must be unique")
        for topic in self.topics:
            questions = [item.casefold() for item in topic.questions]
            if len(set(questions)) != len(questions):
                raise ValueError("topic questions must be unique")
        return self


class TaskEvaluationRequest(BaseModel):
    task_type: Literal["warmup", "read_aloud"]
    reference_text: str = Field(min_length=1, max_length=500)
    transcript: str = Field(default="", max_length=1000)
    asr_confidence: float = Field(default=0.8, ge=0, le=1)


class ReadAloudAttempt(BaseModel):
    reference_text: str = Field(min_length=1, max_length=500)
    transcript: str = Field(default="", max_length=1000)
    asr_confidence: float = Field(default=0.8, ge=0, le=1)


class ReadAloudGroupRequest(BaseModel):
    attempts: list[ReadAloudAttempt] = Field(min_length=1, max_length=10)


class TaskEvaluationResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    fluency: int = Field(ge=0, le=100)
    response_length: int = Field(ge=0, le=100)
    word_accuracy: int = Field(ge=0, le=100)
    pronunciation: int = Field(ge=0, le=100)
    relevance: int = Field(ge=0, le=100)
    feedback: str = Field(max_length=180)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    voice: str | None = None
    speed: Literal["slow", "normal", "fast"] = "normal"


class ASRRequest(BaseModel):
    audio_key: str
    lang: Literal["en"] = "en"


class PronunciationRequest(BaseModel):
    audio_key: str
    reference_text: str
    hypothesis: str = ""
    confidence: float = Field(default=0.8, ge=0, le=1)


class LoudRecordRequest(BaseModel):
    audio_key: str
    context: Literal["warmup", "turn", "shoutout"]
    rms: float = Field(default=0, ge=0, le=1)
    duration_ms: int = Field(default=0, ge=0, le=300_000)


class CoachRequest(BaseModel):
    topic_id: int = 1
    question: str
    transcript: str
    history: list[dict[str, str]] = Field(default_factory=list)
    user_profile: dict[str, str] = Field(default_factory=dict)
    asr_confidence: float = Field(default=0.8, ge=0, le=1)
