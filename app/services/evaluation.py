from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlmodel import Session

from app.models import TaskEvaluation, Turn
from app.models.schemas import (
    CoachResult,
    ReadAloudGroupRequest,
    TaskEvaluationRequest,
    TaskEvaluationResult,
)
from app.skills.pronunciation_skill import grade

WORDS = re.compile(r"[a-z']+")


def _tokens(value: str) -> list[str]:
    return WORDS.findall(value.lower())


def _supportive_feedback(scores: dict[str, int]) -> str:
    overall = round(sum(scores.values()) / len(scores))
    weakest = min(scores, key=scores.get)
    strengths = {
        "fluency": "Your voice kept a steady rhythm.",
        "response_length": "You completed the full idea.",
        "word_accuracy": "Your words matched the sentence clearly.",
        "pronunciation": "Your pronunciation was easy to follow.",
        "relevance": "You stayed focused on the task.",
    }
    next_steps = {
        "fluency": "Try one more time with a smooth, steady pace.",
        "response_length": "Try to complete every part of the sentence.",
        "word_accuracy": "Listen once more and check each key word.",
        "pronunciation": "Slow down slightly and make each sound clear.",
        "relevance": "Keep your words closely connected to the prompt.",
    }
    strongest = max(scores, key=scores.get)
    if overall >= 90:
        return f"{strengths[strongest]} That was confident and polished."
    return f"{strengths[strongest]} {next_steps[weakest]}"


def evaluate_read_aloud(
    payload: TaskEvaluationRequest,
) -> TaskEvaluationResult:
    reference = _tokens(payload.reference_text)
    spoken = _tokens(payload.transcript)
    similarity = round(SequenceMatcher(None, reference, spoken).ratio() * 100)
    if reference and spoken:
        length_ratio = min(len(spoken) / len(reference), len(reference) / len(spoken))
        response_length = round(length_ratio * 100)
    else:
        response_length = 0
    pronunciation = grade(
        payload.reference_text,
        payload.transcript,
        payload.asr_confidence,
    ).score
    confidence_score = max(
        0, min(100, round((payload.asr_confidence - 0.35) / 0.65 * 100))
    )
    scores = {
        "fluency": round((confidence_score * 0.65) + (response_length * 0.35)),
        "response_length": response_length,
        "word_accuracy": similarity,
        "pronunciation": pronunciation,
        "relevance": similarity,
    }
    overall = round(sum(scores.values()) / len(scores) * 0.95)
    return TaskEvaluationResult(
        overall_score=overall,
        feedback=_supportive_feedback(scores),
        **scores,
    )


def _average_results(results: list[TaskEvaluationResult]) -> TaskEvaluationResult:
    keys = (
        "fluency",
        "response_length",
        "word_accuracy",
        "pronunciation",
        "relevance",
    )
    scores = {
        key: round(sum(getattr(item, key) for item in results) / len(results))
        for key in keys
    }
    return TaskEvaluationResult(
        overall_score=round(sum(item.overall_score for item in results) / len(results)),
        feedback=_supportive_feedback(scores),
        **scores,
    )


def evaluate_read_aloud_group(
    payload: ReadAloudGroupRequest,
) -> TaskEvaluationResult:
    results = [
        evaluate_read_aloud(
            TaskEvaluationRequest(
                task_type="read_aloud",
                reference_text=item.reference_text,
                transcript=item.transcript,
                asr_confidence=item.asr_confidence,
            )
        )
        for item in payload.attempts
    ]
    return _average_results(results)


def evaluate_topic_turns(turns: list[Turn]) -> TaskEvaluationResult:
    results: list[TaskEvaluationResult] = []
    for turn in turns:
        coach = CoachResult.model_validate_json(turn.coach_json)
        results.append(
            TaskEvaluationResult(
                overall_score=coach.overall_score,
                fluency=coach.scores.fluency,
                response_length=coach.scores.response_length,
                word_accuracy=coach.scores.word_accuracy,
                pronunciation=coach.scores.pronunciation,
                relevance=coach.scores.relevance,
                feedback=coach.brief_feedback,
            )
        )
    if not results:
        empty = {
            key: 0
            for key in (
                "fluency",
                "response_length",
                "word_accuracy",
                "pronunciation",
                "relevance",
            )
        }
        return TaskEvaluationResult(
            overall_score=0,
            feedback="Finish each answer to receive a full topic score.",
            **empty,
        )
    return _average_results(results)


def save_evaluation(
    session: Session,
    user_id: int,
    task_type: str,
    prompt: str,
    transcript: str,
    result: TaskEvaluationResult,
    session_id: int | None = None,
    turn_id: int | None = None,
) -> TaskEvaluation:
    evaluation = TaskEvaluation(
        user_id=user_id,
        session_id=session_id,
        turn_id=turn_id,
        task_type=task_type,
        prompt=prompt,
        transcript=transcript,
        **result.model_dump(),
    )
    session.add(evaluation)
    return evaluation
