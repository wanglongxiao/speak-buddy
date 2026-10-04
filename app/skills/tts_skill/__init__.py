import base64
import hashlib
import json
from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
from fastapi.concurrency import run_in_threadpool

from app.config import ROOT, get_settings
from app.services.voices import DEFAULT_BUDDY_VOICE, valid_buddy_voice
from app.skills.tos_skill import store_audio

SPEED_RATES = {"slow": -15, "normal": 0, "fast": 15}


def selected_voice(voice: str) -> str:
    value = voice or get_settings().byteplus_tts_voice or DEFAULT_BUDDY_VOICE
    if not valid_buddy_voice(value):
        raise ValueError("Unsupported Buddy voice.")
    return value


def request_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "X-Api-Key": settings.speech_api_key,
        "X-Api-Resource-Id": settings.byteplus_tts_resource_id,
        "X-Api-App-Key": "aGjiRDfUWi",
        "X-Api-Request-Id": str(uuid4()),
        "Content-Type": "application/json",
    }


def request_payload(text: str, speed: str, voice: str) -> dict[str, object]:
    return {
        "user": {"uid": "speakbuddy"},
        "req_params": {
            "text": text,
            "speaker": voice,
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000,
                "speech_rate": SPEED_RATES.get(speed, 0),
            },
        },
    }


async def stream_speech(
    text: str,
    speed: str = "normal",
    voice: str = "",
) -> AsyncIterator[bytes]:
    settings = get_settings()
    voice = selected_voice(voice)
    if not settings.speech_enabled:
        return
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream(
                "POST",
                settings.byteplus_tts_url,
                headers=request_headers(),
                json=request_payload(text, speed, voice),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    item = json.loads(line.removeprefix("data:").strip())
                    encoded = item.get("data") or item.get("audio")
                    if encoded:
                        yield base64.b64decode(encoded)
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        return


async def synthesize(text: str, speed: str = "normal", voice: str = "") -> str:
    """Synthesize a supported English voice; the browser is the last fallback."""
    settings = get_settings()
    voice = selected_voice(voice)

    cache_name = hashlib.sha256(f"{voice}|{speed}|{text}".encode()).hexdigest()[:24]
    audio_dir = getattr(settings, "audio_dir", ROOT / "data" / "audio")
    output = audio_dir / f"tts-{cache_name}.mp3"
    if output.exists():
        return f"/audio/{output.name}"
    if not settings.speech_enabled:
        return ""

    chunks = bytearray()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream(
                "POST",
                settings.byteplus_tts_url,
                headers=request_headers(),
                json=request_payload(text, speed, voice),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    item = json.loads(line.removeprefix("data:").strip())
                    encoded = item.get("data") or item.get("audio")
                    if encoded:
                        chunks.extend(base64.b64decode(encoded))
        if chunks:
            stored = await run_in_threadpool(
                store_audio,
                bytes(chunks),
                output.name,
                "audio/mpeg",
            )
            return stored.url
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        return ""
    return ""
