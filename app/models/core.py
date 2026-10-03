from datetime import UTC, datetime
from datetime import date as Date

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str | None = Field(default=None, index=True)
    password_hash: str | None = None
    nickname: str = "Star Speaker"
    lang: str = "en"
    default_difficulty: str = "normal"
    default_speed: str = "normal"
    buddy_voice: str = "en_female_skye_emo_v2_mars_bigtts"
    total_xp: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class Topic(SQLModel, table=True):
    __tablename__ = "topics"

    id: int | None = Field(default=None, primary_key=True)
    owner_user_id: int | None = Field(default=None, foreign_key="users.id")
    daily_content_id: int | None = Field(
        default=None, foreign_key="daily_practice_content.id"
    )
    title: str
    difficulty: str = "normal"
    starter_question: str
    follow_up_hints_json: str = "[]"
    ideal_answer: str = ""
    suggested_words_json: str = "[]"
    is_system: bool = True


class PracticeSession(SQLModel, table=True):
    __tablename__ = "sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    topic_id: int | None = Field(default=None, foreign_key="topics.id")
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    difficulty: str = "normal"
    speed: str = "normal"
    total_xp: int = 0
    loud_seconds: int = 0


class Turn(SQLModel, table=True):
    __tablename__ = "turns"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id")
    topic_id: int = Field(foreign_key="topics.id")
    question: str
    audio_key: str = ""
    transcript: str = ""
    confidence: float = 0.0
    coach_json: str = "{}"
    scores_json: str = "{}"
    xp: int = 0
    echo_score: int | None = None
    created_at: datetime = Field(default_factory=utcnow)


class LoudMeter(SQLModel, table=True):
    __tablename__ = "loud_meter"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    date: Date = Field(default_factory=Date.today, index=True)
    total_seconds: int = 0
    shoutout_count: int = 0
    warmup_count: int = 0
