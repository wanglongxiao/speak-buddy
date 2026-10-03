from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlmodel import Session, col, select

from app.compat import HONG_KONG, UTC
from app.models import LoudMeter, PracticeSession, TaskEvaluation, Turn, User
from app.skills.gamify_skill import title_for

PERIOD_DAYS = {"day": 1, "week": 7, "month": 30}


def _average_score(turn: Turn) -> int | None:
    try:
        scores = json.loads(turn.scores_json or "{}")
        return round(sum(scores.values()) / len(scores)) if scores else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _evaluation(score: int, turn_count: int, lang: str) -> str:
    if turn_count == 0:
        return (
            "新的练习周期已经开始，每一次开口都会让表达更自然。"
            if lang == "zh"
            else "A fresh practice window is open; every brave word will build fluency."
        )
    bands = (
        (
            65,
            "你正在勇敢开口，坚持练习会让句子越来越流畅。",
            "Your brave voice is showing up, and steady practice will make "
            "each sentence flow.",
        ),
        (
            80,
            "你的表达越来越清楚，也更愿意自信地说完整句子。",
            "Your ideas are becoming clearer, and your full sentences sound "
            "more confident.",
        ),
        (
            90,
            "你的口语基础很稳，表达已经自然又有细节。",
            "Your speaking foundation is strong, with natural ideas and "
            "useful detail.",
        ),
        (
            101,
            "你的表达自信、清晰又丰富，已经能从容讨论不同观点。",
            "Your voice is confident, clear, and ready for thoughtful discussion.",
        ),
    )
    for ceiling, zh, en in bands:
        if score < ceiling:
            return zh if lang == "zh" else en
    return bands[-1][1 if lang == "zh" else 2]


def _date_range(start: date, days: int) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(days)]


def _local_time(value: datetime) -> datetime:
    aware = value if value.tzinfo else value.replace(tzinfo=UTC)
    return aware.astimezone(HONG_KONG)


def build_progress(
    session: Session, user: User, period: str, lang: str
) -> dict[str, object]:
    period = period if period in PERIOD_DAYS else "week"
    days = PERIOD_DAYS[period]
    today = datetime.now(HONG_KONG).date()
    start_date = today - timedelta(days=days - 1)
    start_at = datetime.combine(
        start_date,
        time.min,
        tzinfo=HONG_KONG,
    ).astimezone(UTC)

    sessions = session.exec(
        select(PracticeSession).where(
            PracticeSession.user_id == user.id,
            PracticeSession.started_at >= start_at,
        )
    ).all()
    turns = session.exec(
        select(Turn)
        .join(PracticeSession)
        .where(
            PracticeSession.user_id == user.id,
            Turn.created_at >= start_at,
        )
        .order_by(col(Turn.created_at))
    ).all()
    loud = session.exec(
        select(LoudMeter).where(
            LoudMeter.user_id == user.id,
            LoudMeter.date >= start_date,
        )
    ).all()

    evaluations = session.exec(
        select(TaskEvaluation)
        .where(
            TaskEvaluation.user_id == user.id,
            TaskEvaluation.created_at >= start_at,
        )
        .order_by(col(TaskEvaluation.created_at))
    ).all()
    evaluated_turn_ids = {
        item.turn_id for item in evaluations if item.turn_id is not None
    }
    evaluated_session_ids = {
        item.session_id
        for item in evaluations
        if item.task_type == "topic" and item.session_id is not None
    }
    legacy_turns = [
        turn
        for turn in turns
        if turn.id not in evaluated_turn_ids
        and turn.session_id not in evaluated_session_ids
    ]
    legacy_scored = [
        (turn.created_at, score)
        for turn in legacy_turns
        if (score := _average_score(turn)) is not None
    ]
    if evaluations:
        scored = [
            (item.created_at, item.overall_score) for item in evaluations
        ] + legacy_scored
        scored.sort(key=lambda item: item[0])
        words_spoken = sum(len(item.transcript.split()) for item in evaluations) + sum(
            len(item.transcript.split()) for item in legacy_turns
        )
        rubric_scores = {
            key: round(
                sum(getattr(item, key) for item in evaluations) / len(evaluations)
            )
            for key in (
                "fluency",
                "response_length",
                "word_accuracy",
                "pronunciation",
                "relevance",
            )
        }
    else:
        scored = legacy_scored
        words_spoken = sum(len(item.transcript.split()) for item in turns)
        rubric_scores = {}
    scores = [score for _, score in scored]
    by_date: dict[date, list[int]] = defaultdict(list)
    for created_at, score in scored:
        by_date[_local_time(created_at).date()].append(score)
    if period == "day":
        labels = [_local_time(created_at).strftime("%H:%M") for created_at, _ in scored]
        values = scores
    else:
        dates = _date_range(start_date, days)
        labels = [item.strftime("%b %d") for item in dates]
        values = [
            round(sum(by_date[item]) / len(by_date[item])) if by_date[item] else None
            for item in dates
        ]
    active_dates = {_local_time(item.started_at).date() for item in sessions}
    active_dates.update(item.date for item in loud if item.total_seconds)
    active_dates.update(_local_time(item.created_at).date() for item in evaluations)
    average = round(sum(scores) / len(scores)) if scores else 0
    task_count = len(evaluations) + len(legacy_turns)
    return {
        "period": period,
        "title": title_for(user.total_xp),
        "completed_quests": sum(item.finished_at is not None for item in sessions),
        "average_score": average,
        "loud_seconds_period": sum(item.total_seconds for item in loud),
        "active_days": len(active_dates),
        "words_spoken": words_spoken,
        "turn_count": task_count,
        "rubric_scores": rubric_scores,
        "chart_labels": labels,
        "chart_values": values,
        "evaluation": _evaluation(average, task_count, lang),
    }
