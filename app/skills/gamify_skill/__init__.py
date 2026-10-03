from dataclasses import dataclass, field

TITLES = [
    (12_000, "Legendary Speaker"),
    (6_000, "Golden Voice"),
    (2_500, "Story Weaver"),
    (1_000, "Brave Lioness"),
    (300, "Chatty Robin"),
    (0, "Little Sprout"),
]


@dataclass(slots=True)
class Reward:
    xp: int
    title: str
    badges: list[str] = field(default_factory=list)
    celebration: str | None = None


def title_for(total_xp: int) -> str:
    return next(title for threshold, title in TITLES if total_xp >= threshold)


def evaluate(event: str, context: dict[str, int | float | bool]) -> Reward:
    """Keep rewards deterministic so retries cannot change learning feedback."""
    current_xp = int(context.get("total_xp", 0))
    badges: list[str] = []
    xp = 0
    if event == "warmup":
        xp = 5
    elif event == "echo" and float(context.get("score", 0)) >= 80:
        xp = 5
    elif event == "quest_complete":
        xp = 20
        badges.append("first-flight")
        if bool(context.get("challenge")):
            badges.append("challenger")
    elif event == "shoutout":
        count = int(context.get("count", 0))
        if count >= 10:
            xp, badges = 20, ["daily-shouter"]
    elif event == "turn":
        xp = max(10, min(30, int(context.get("coach_xp", 10))))

    if int(context.get("loud_seconds", 0)) >= 300:
        badges.append("loud-legend")
    if int(context.get("streak_days", 0)) >= 7:
        badges.append("seven-day")
    if float(context.get("average", 0)) >= 95:
        badges.append("perfect-score")

    old_title = title_for(current_xp)
    new_title = title_for(current_xp + xp)
    celebration = f"New title: {new_title}" if new_title != old_title else None
    return Reward(
        xp=xp,
        title=new_title,
        badges=list(dict.fromkeys(badges)),
        celebration=celebration,
    )
