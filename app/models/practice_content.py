from datetime import date, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.core import utcnow


class PracticeContentRelease(SQLModel, table=True):
    __tablename__ = "practice_content_releases"

    id: int | None = Field(default=None, primary_key=True)
    created_by_user_id: int = Field(foreign_key="users.id", index=True)
    content_date: date = Field(default_factory=date.today, index=True)
    difficulty: str = Field(default="normal", index=True)
    topics_json: str = "[]"
    read_aloud_json: str = "[]"
    generation_provider: str = "fallback"
    created_at: datetime = Field(default_factory=utcnow, index=True)
    expires_at: datetime


class DailyPracticeContent(SQLModel, table=True):
    __tablename__ = "daily_practice_content"
    __table_args__ = (
        UniqueConstraint("user_id", "content_date", name="uq_daily_content_user_date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    source_release_id: int | None = Field(
        default=None, foreign_key="practice_content_releases.id", index=True
    )
    content_date: date = Field(default_factory=date.today, index=True)
    difficulty: str = "normal"
    read_aloud_json: str = "[]"
    generation_provider: str = "fallback"
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime


class TaskEvaluation(SQLModel, table=True):
    __tablename__ = "task_evaluations"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    session_id: int | None = Field(default=None, foreign_key="sessions.id")
    turn_id: int | None = Field(default=None, foreign_key="turns.id")
    task_type: str = Field(index=True)
    prompt: str
    transcript: str
    overall_score: int
    fluency: int
    response_length: int
    word_accuracy: int
    pronunciation: int
    relevance: int
    feedback: str
    created_at: datetime = Field(default_factory=utcnow, index=True)
