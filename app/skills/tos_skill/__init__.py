from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.config import ROOT, get_settings

KEY_PATTERN = re.compile(
    r"^recordings/(?:[0-9]+/)?[a-f0-9]{32}\.(webm|wav|mp3|m4a|ogg)$"
)


@dataclass
class StoredAudio:
    key: str
    url: str
    local_path: Path | None
    provider: str


def _extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in {".webm", ".wav", ".mp3", ".m4a", ".ogg"} else ".webm"


def audio_url(key: str) -> str:
    """Issue a fresh, short-lived read URL for audio in a private bucket."""
    if not KEY_PATTERN.fullmatch(key):
        raise ValueError("Invalid audio key")
    settings = get_settings()
    if settings.tos_enabled:
        import tos

        client = tos.TosClientV2(
            settings.byteplus_ak,
            settings.byteplus_sk,
            settings.tos_endpoint,
            settings.tos_region,
            request_timeout=15, connection_time=5, socket_timeout=15,
            max_retry_count=0,
        )
        try:
            return client.pre_signed_url(
                tos.HttpMethodType.Http_Method_Get,
                settings.tos_bucket,
                key,
                expires=3600,
            ).signed_url
        finally:
            client.close()
    host = settings.tos_endpoint.removeprefix("https://").rstrip("/")
    return f"https://{settings.tos_bucket}.{host}/{key}"


def store_audio(
    data: bytes, filename: str, content_type: str, owner_id: int | None = None
) -> StoredAudio:
    """Prefer TOS but make a complete local quest possible during outages."""
    settings = get_settings()
    prefix = f"{owner_id}/" if owner_id is not None else ""
    key = f"recordings/{prefix}{uuid4().hex}{_extension(filename)}"
    if settings.tos_enabled:
        try:
            import tos

            client = tos.TosClientV2(
                settings.byteplus_ak,
                settings.byteplus_sk,
                settings.tos_endpoint,
                settings.tos_region,
                request_timeout=15, connection_time=5, socket_timeout=15,
                max_retry_count=0,
            )
            try:
                client.put_object(
                    settings.tos_bucket,
                    key,
                    content=data,
                    content_type=content_type,
                )
            finally:
                client.close()
            return StoredAudio(key, f"/api/audio/{key}", None, "tos")
        except Exception:
            if settings.app_env == "production":
                raise RuntimeError("Audio storage is unavailable") from None

    audio_dir = getattr(settings, "audio_dir", ROOT / "data" / "audio")
    audio_dir.mkdir(parents=True, exist_ok=True)
    local_path = audio_dir / Path(key).name
    local_path.write_bytes(data)
    return StoredAudio(
        key=f"local:{local_path.name}",
        url=f"/audio/{local_path.name}",
        local_path=local_path,
        provider="local",
    )


def resolve_audio(key: str) -> StoredAudio | None:
    if not key.startswith("local:"):
        return None
    settings = get_settings()
    audio_dir = getattr(settings, "audio_dir", ROOT / "data" / "audio")
    name = key.removeprefix("local:")
    if Path(name).name != name or not re.fullmatch(
        r"[a-f0-9]{32}\.(webm|wav|mp3|m4a|ogg)", name
    ):
        raise ValueError("Invalid local audio key")
    path = audio_dir / name
    if not path.exists():
        return None
    return StoredAudio(key, f"/audio/{path.name}", path, "local")
