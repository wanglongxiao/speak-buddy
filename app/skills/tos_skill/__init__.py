from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.config import ROOT, get_settings


@dataclass(slots=True)
class StoredAudio:
    key: str
    url: str
    local_path: Path | None
    provider: str


def _extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in {".webm", ".wav", ".mp3", ".m4a", ".ogg"} else ".webm"


def store_audio(data: bytes, filename: str, content_type: str) -> StoredAudio:
    """Prefer TOS but make a complete local quest possible during outages."""
    settings = get_settings()
    key = f"recordings/{uuid4().hex}{_extension(filename)}"
    if settings.tos_enabled:
        try:
            import tos

            client = tos.TosClientV2(
                settings.byteplus_ak,
                settings.byteplus_sk,
                settings.tos_endpoint,
                settings.tos_region,
            )
            client.put_object(
                settings.tos_bucket,
                key,
                content=data,
                content_type=content_type,
            )
            host = settings.tos_endpoint.removeprefix("https://").rstrip("/")
            url = f"https://{settings.tos_bucket}.{host}/{key}"
            return StoredAudio(key, url, None, "tos")
        except Exception:
            pass

    audio_dir = ROOT / "data" / "audio"
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
    path = ROOT / "data" / "audio" / key.removeprefix("local:")
    if not path.exists():
        return None
    return StoredAudio(key, f"/audio/{path.name}", path, "local")
