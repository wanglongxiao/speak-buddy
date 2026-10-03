import re
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class PronunciationResult:
    score: int
    word_match: float
    confidence: float
    feedback: str
    echo_bonus: bool


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def grade(
    reference: str,
    hypothesis: str,
    confidence: float,
) -> PronunciationResult:
    """Blend lexical match and ASR certainty without claiming phoneme accuracy."""
    match = SequenceMatcher(None, _words(reference), _words(hypothesis)).ratio()
    safe_confidence = max(0.0, min(1.0, confidence))
    score = round(100 * (0.6 * match + 0.4 * safe_confidence))
    if score >= 80:
        feedback, bonus = "Beautiful echo - you made it sound natural!", True
    elif score >= 60:
        feedback, bonus = "Almost! One more try?", False
    else:
        feedback, bonus = "Every try builds your voice. Listen once more!", False
    return PronunciationResult(
        score=score,
        word_match=round(match, 3),
        confidence=safe_confidence,
        feedback=feedback,
        echo_bonus=bonus,
    )
