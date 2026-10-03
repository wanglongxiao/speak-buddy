from __future__ import annotations

from datetime import date, datetime

from sqlmodel import Field, SQLModel

from app.models.core import utcnow


class Badge(SQLModel, table=True):
    __tablename__ = "badges"

    code: str = Field(primary_key=True)
    name_en: str
    name_zh: str
    desc_en: str
    desc_zh: str
    svg_path: str


class BadgeAward(SQLModel, table=True):
    __tablename__ = "badge_awards"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    badge_code: str = Field(foreign_key="badges.code")
    awarded_at: datetime = Field(default_factory=utcnow)


class Streak(SQLModel, table=True):
    __tablename__ = "streaks"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    current_days: int = 0
    longest_days: int = 0
    last_date: date | None = None


class Score(SQLModel, table=True):
    __tablename__ = "scores"

    id: int | None = Field(default=None, primary_key=True)
    turn_id: int = Field(foreign_key="turns.id")
    pronunciation: int
    fluency: int
    vocabulary: int
    confidence: int

    @property
    def average(self) -> float:
        return (
            self.pronunciation + self.fluency + self.vocabulary + self.confidence
        ) / 4
