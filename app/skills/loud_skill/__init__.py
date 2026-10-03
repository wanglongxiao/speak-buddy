from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

QUIET_RMS = 0.035


@dataclass
class LoudResult:
    rms: float
    duration_ms: int
    counted_seconds: int
    is_quiet: bool


def measure_wav(path: Path) -> tuple[float, int]:
    with wave.open(str(path), "rb") as audio:
        frames = audio.readframes(audio.getnframes())
        sample_width = audio.getsampwidth()
        duration_ms = round(audio.getnframes() / audio.getframerate() * 1000)
    if sample_width != 2 or not frames:
        return 0.0, duration_ms
    samples = struct.unpack(f"<{len(frames) // 2}h", frames)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    return round(rms / 32768, 4), duration_ms


def assess(
    rms: float,
    duration_ms: int,
    *,
    wav_path: Path | None = None,
) -> LoudResult:
    """Count active speech while treating unknown volume as neutral."""
    measured_rms, measured_ms = rms, duration_ms
    if wav_path and wav_path.exists() and (rms <= 0 or duration_ms <= 0):
        measured_rms, measured_ms = measure_wav(wav_path)
    is_quiet = 0 < measured_rms < QUIET_RMS
    counted = round(measured_ms / 1000) if measured_rms >= QUIET_RMS else 0
    return LoudResult(
        rms=round(measured_rms, 4),
        duration_ms=measured_ms,
        counted_seconds=max(0, counted),
        is_quiet=is_quiet,
    )
