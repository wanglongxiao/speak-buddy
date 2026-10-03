import json
from functools import lru_cache
from pathlib import Path

from fastapi import Request

I18N_DIR = Path(__file__).resolve().parent.parent / "i18n"


@lru_cache
def messages(lang: str) -> dict[str, object]:
    safe_lang = lang if lang in {"en", "zh"} else "en"
    return json.loads((I18N_DIR / f"{safe_lang}.json").read_text("utf-8"))


def language_for(request: Request) -> str:
    query_lang = request.query_params.get("lang")
    if query_lang in {"en", "zh"}:
        return query_lang
    return request.cookies.get("lang", "en")


def context_for(request: Request) -> dict[str, object]:
    lang = language_for(request)
    return {"request": request, "lang": lang, "t": messages(lang)}
