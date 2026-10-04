import gzip
import json
import struct
from dataclasses import dataclass
from uuid import uuid4

from websockets.asyncio.client import ClientConnection, connect

from app.config import get_settings

CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ERROR_RESPONSE = 0b1111
POSITIVE_SEQUENCE = 0b0001
NEGATIVE_SEQUENCE = 0b0011
JSON_SERIALIZATION = 0b0001
GZIP_COMPRESSION = 0b0001


@dataclass
class StreamingASRResult:
    text: str = ""
    final: bool = False
    error: str = ""


def _header(message_type: int, flags: int) -> bytes:
    return bytes(
        [
            (0b0001 << 4) | 1,
            (message_type << 4) | flags,
            (JSON_SERIALIZATION << 4) | GZIP_COMPRESSION,
            0,
        ]
    )


def _full_request(sequence: int) -> bytes:
    payload = gzip.compress(
        json.dumps(
            {
                "user": {"uid": "speakbuddy"},
                "audio": {
                    "format": "pcm",
                    "codec": "raw",
                    "rate": 16000,
                    "bits": 16,
                    "channel": 1,
                },
                "request": {
                    "model_name": "bigmodel",
                    "language": "en-US",
                    "enable_itn": True,
                    "enable_punc": True,
                    "enable_ddc": True,
                    "show_utterances": True,
                    "enable_nonstream": True,
                    "end_window_size": 650,
                },
            }
        ).encode()
    )
    return (
        _header(CLIENT_FULL_REQUEST, POSITIVE_SEQUENCE)
        + struct.pack(">iI", sequence, len(payload))
        + payload
    )


def _audio_request(sequence: int, audio: bytes, final: bool = False) -> bytes:
    payload = gzip.compress(audio)
    flags = NEGATIVE_SEQUENCE if final else POSITIVE_SEQUENCE
    if final:
        sequence = -sequence
    return (
        _header(CLIENT_AUDIO_REQUEST, flags)
        + struct.pack(">iI", sequence, len(payload))
        + payload
    )


def _parse_response(message: bytes) -> StreamingASRResult:
    if len(message) < 4:
        return StreamingASRResult(error="Invalid ASR response")
    header_size = (message[0] & 0x0F) * 4
    message_type = message[1] >> 4
    flags = message[1] & 0x0F
    serialization = message[2] >> 4
    compression = message[2] & 0x0F
    payload = message[header_size:]

    if flags & 0x01:
        payload = payload[4:]
    final = bool(flags & 0x02)
    if flags & 0x04:
        payload = payload[4:]

    if message_type == SERVER_ERROR_RESPONSE:
        code = struct.unpack(">i", payload[:4])[0]
        size = struct.unpack(">I", payload[4:8])[0]
        detail = payload[8 : 8 + size].decode(errors="replace")
        return StreamingASRResult(error=f"{code}: {detail}", final=True)
    if message_type != SERVER_FULL_RESPONSE or len(payload) < 4:
        return StreamingASRResult(final=final)

    size = struct.unpack(">I", payload[:4])[0]
    payload = payload[4 : 4 + size]
    if compression == GZIP_COMPRESSION and payload:
        payload = gzip.decompress(payload)
    if serialization != JSON_SERIALIZATION or not payload:
        return StreamingASRResult(final=final)

    data = json.loads(payload.decode())
    result = data.get("result") or {}
    utterances = result.get("utterances") or []
    definite = any(item.get("definite") for item in utterances)
    return StreamingASRResult(
        text=str(result.get("text") or ""),
        final=final or definite,
    )


class SeedASRStream:
    def __init__(self) -> None:
        self.connection: ClientConnection | None = None
        self.sequence = 1

    async def connect(self) -> None:
        settings = get_settings()
        headers = {
            "X-Api-Key": settings.speech_api_key,
            "X-Api-Resource-Id": settings.byteplus_asr_stream_resource_id,
            "X-Api-Request-Id": str(uuid4()),
        }
        self.connection = await connect(
            settings.byteplus_asr_stream_url,
            additional_headers=headers,
            compression=None,
            open_timeout=8,
            ping_interval=20,
        )
        await self.connection.send(_full_request(self.sequence))
        self.sequence += 1
        await self.connection.recv()

    async def send_audio(self, audio: bytes) -> None:
        if not self.connection:
            raise RuntimeError("ASR stream is not connected")
        await self.connection.send(_audio_request(self.sequence, audio))
        self.sequence += 1

    async def finish(self) -> None:
        if self.connection:
            await self.connection.send(_audio_request(self.sequence, b"", final=True))

    async def receive(self) -> StreamingASRResult:
        if not self.connection:
            raise RuntimeError("ASR stream is not connected")
        message = await self.connection.recv()
        if not isinstance(message, bytes):
            return StreamingASRResult(error=str(message), final=True)
        return _parse_response(message)

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()
