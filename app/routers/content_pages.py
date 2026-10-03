from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.db import get_session
from app.services.auth import request_user
from app.services.content_releases import latest_release
from app.services.daily_content import ensure_daily_content

router = APIRouter()


@router.post("/content/refresh")
async def refresh_content(request: Request, session: Session = Depends(get_session)):
    user = request_user(request, session)
    batch = await ensure_daily_content(session, user, force=True)
    release = latest_release(session, user.default_difficulty)
    status = "pending" if release and batch.source_release_id != release.id else "1"
    return RedirectResponse(f"/topics?updated={status}", status_code=303)
