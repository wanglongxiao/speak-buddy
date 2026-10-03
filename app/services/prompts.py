from functools import lru_cache
from pathlib import Path

PLANS_DIR = Path(__file__).resolve().parent.parent.parent / "plans"


@lru_cache
def load_prompt(filename: str) -> str:
    """Load editable prompts from plans without embedding policy in code."""
    safe_name = Path(filename).name
    return (PLANS_DIR / safe_name).read_text("utf-8")
