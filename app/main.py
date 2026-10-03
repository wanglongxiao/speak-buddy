from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.config import ROOT, get_settings
from app.db import engine, init_db
from app.routers import (
    api,
    auth_pages,
    content_pages,
    evaluation_api,
    insights_api,
    pages,
    progress_pages,
    quest_api,
    settings_pages,
    topic_api,
)
from app.services.daily_content import cleanup_expired_content


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings()
    init_db()
    with Session(engine) as session:
        cleanup_expired_content(session)
    yield


app = FastAPI(title="SpeakBuddy", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
audio_dir = get_settings().audio_dir
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")
app.include_router(pages.router)
app.include_router(auth_pages.router)
app.include_router(content_pages.router)
app.include_router(progress_pages.router)
app.include_router(settings_pages.router)
app.include_router(api.router)
app.include_router(quest_api.router)
app.include_router(evaluation_api.router)
app.include_router(topic_api.router)
app.include_router(insights_api.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
