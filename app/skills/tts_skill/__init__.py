import base64
import hashlib
import json
from uuid import uuid4

import httpx

from app.config import ROOT, get_settings

SPEED_RATES = {"slow": -15, "normal": 0, "fast": 15}
VERIFIED_EN_US_VOICES = {"en_female_skye_emo_v2_mars_bigtts"}


async def synthesize(text: str, speed: str = "normal", voice: str = "") -> str:
    """Synthesize one consistent en-US voice; the browser is the last fallback."""
    settings = get_settings()
    selected_voice = voice or settings.byteplus_tts_voice
    normalized = selected_voice.lower().replace("-", "_")
    if not normalized.startswith("en_us") and normalized not in VERIFIED_EN_US_VOICES:
        raise ValueError("Only a verified en-US Buddy voice is allowed.")

    cache_name = hashlib.sha256(
        f"{selected_voice}|{speed}|{text}".encode()
    ).hexdigest()[:24]
    output = ROOT / "data" / "audio" / f"tts-{cache_name}.mp3"
    if output.exists():
        return f"/audio/{output.name}"
    if not settings.speech_enabled:
        return ""

    headers = {
        "X-Api-Key": settings.speech_api_key,
        "X-Api-Resource-Id": settings.byteplus_tts_resource_id,
        "X-Api-App-Key": "aGjiRDfUWi",
        "X-Api-Request-Id": str(uuid4()),
        "Content-Type": "application/json",
    }
    payload = {
        "user": {"uid": "speakbuddy"},
        "req_params": {
            "text": text,
            "speaker": selected_voice,
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000,
                "speech_rate": SPEED_RATES.get(speed, 0),
            },
        },
    }
    chunks = bytearray()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream(
                "POST", settings.byteplus_tts_url, headers=headers, json=payload
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
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(chunks)
            return f"/audio/{output.name}"
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        return ""
    return ""
