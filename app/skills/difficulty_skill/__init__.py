from dataclasses import dataclass


@dataclass
class DifficultyAdvice:
    difficulty: str
    speed: str
    rolling_average: float
    invite_level_up: bool
    frustration_recovery: bool


@dataclass(frozen=True)
class DifficultyProfile:
    code: str
    min_words: int
    max_words: int
    vocabulary: str


PROFILES = {
    "easy": DifficultyProfile("easy", 6, 10, "common A2 words"),
    "normal": DifficultyProfile("normal", 10, 16, "everyday B1 words"),
    "hard": DifficultyProfile("hard", 15, 22, "richer B1-B2 words"),
    "expert": DifficultyProfile("expert", 20, 30, "precise B2 words"),
}


def normalize(value: str) -> str:
    aliases = {"medium": "normal", "challenge": "hard"}
    normalized = aliases.get(value, value)
    return normalized if normalized in PROFILES else "normal"


def profile_for(value: str) -> DifficultyProfile:
    return PROFILES[normalize(value)]


def question_for(title: str, difficulty: str, fallback: str = "") -> str:
    level = normalize(difficulty)
    if level == "easy":
        return f"What do you enjoy most about {title.lower()}?"
    if level == "normal" and fallback:
        return fallback
    if level == "normal":
        return (
            f"Can you share a recent experience about {title.lower()} and explain it?"
        )
    if level == "hard":
        return (
            f"Thinking about {title.lower()}, can you describe a recent experience "
            "and explain why it mattered to you?"
        )
    return (
        f"When you think about {title.lower()}, how would you compare different "
        "viewpoints, support your opinion with an example, and respond to disagreement?"
    )


def recommend(recent_scores: list[float]) -> DifficultyAdvice:
    """Recommend without silently lowering the learner's saved level."""
    window = recent_scores[-10:]
    average = round(sum(window) / len(window), 1) if window else 65.0
    if average < 60:
        difficulty, speed = "easy", "slow"
    elif average < 80:
        difficulty, speed = "normal", "normal"
    elif average < 92:
        difficulty, speed = "hard", "normal"
    else:
        difficulty, speed = "expert", "normal"
    return DifficultyAdvice(
        difficulty=difficulty,
        speed=speed,
        rolling_average=average,
        invite_level_up=len(window) >= 3 and all(score >= 85 for score in window[-3:]),
        frustration_recovery=len(window) >= 2
        and all(score < 50 for score in window[-2:]),
    )
