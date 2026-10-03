from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.db import get_session
from app.models.schemas import ReadAloudGroupRequest, TaskEvaluationRequest
from app.services.auth import request_user
from app.services.evaluation import (
    evaluate_read_aloud,
    evaluate_read_aloud_group,
    save_evaluation,
)

router = APIRouter(prefix="/api")


@router.post("/evaluate-task")
def evaluate_task(
    payload: TaskEvaluationRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    user = request_user(request, session)
    result = evaluate_read_aloud(payload)
    save_evaluation(
        session,
        user.id or 0,
        payload.task_type,
        payload.reference_text,
        payload.transcript,
        result,
    )
    session.commit()
    return result


@router.post("/evaluate-read-aloud-group")
def evaluate_read_aloud_group_api(
    payload: ReadAloudGroupRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    user = request_user(request, session)
    result = evaluate_read_aloud_group(payload)
    save_evaluation(
        session,
        user.id or 0,
        "read_aloud",
        "\n".join(item.reference_text for item in payload.attempts),
        "\n".join(item.transcript for item in payload.attempts),
        result,
    )
    session.commit()
    return result
