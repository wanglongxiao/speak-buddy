import asyncio
import uuid
from dataclasses import dataclass

import httpx

from app.config import get_settings


@dataclass(slots=True)
class ASRResult:
    transcript: str
    confidence: float
    duration_ms: int
    provider: str = "fallback"


async def transcribe(
    audio_url: str,
    duration_ms: int = 0,
    fallback_text: str = "I am ready to share my idea today.",
) -> ASRResult:
    """Use Seed-ASR when reachable while keeping local demos speakable."""
    settings = get_settings()
    if not settings.speech_enabled or not audio_url.startswith("http"):
        return ASRResult(fallback_text, 0.82, duration_ms)

    request_id = str(uuid.uuid4())
    headers = {
        "X-Api-Key": settings.speech_api_key,
        "X-Api-Resource-Id": settings.byteplus_asr_resource_id,
        "X-Api-Request-Id": request_id,
        "X-Api-Sequence": "-1",
    }
    payload = {
        "user": {"uid": "speakbuddy"},
        "audio": {"url": audio_url},
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "language": "en-US",
        },
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            submit = await client.post(
                f"{settings.byteplus_asr_url}/submit",
                headers=headers,
                json=payload,
            )
            submit.raise_for_status()
            for _ in range(10):
                await asyncio.sleep(0.4)
                response = await client.post(
                    f"{settings.byteplus_asr_url}/query",
                    headers=headers,
                    json={},
                )
                if response.headers.get("X-Api-Status-Code") == "20000000":
                    data = response.json()
                    result = data.get("result", {})
                    text = result.get("text") or result.get("utterances", [{}])[0].get(
                        "text", ""
                    )
                    confidence = float(result.get("confidence", 0.8))
                    return ASRResult(
                        text or fallback_text,
                        confidence,
                        duration_ms,
                        "seed",
                    )
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        pass
    return ASRResult(fallback_text, 0.62, duration_ms)
