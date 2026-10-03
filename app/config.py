from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///data/speakbuddy.db"
    local_data_dir: str = "data"
    mock_ai: bool = True
    session_secret: str = "speakbuddy-local-session-secret"

    byteplus_ak: str = ""
    byteplus_sk: str = ""
    tos_region: str = "ap-southeast-1"
    tos_bucket: str = ""
    tos_endpoint: str = "https://tos-ap-southeast-1.bytepluses.com"

    speech_appid: str = ""
    speech_api_key: str = ""
    byteplus_asr_url: str = (
        "https://voice.ap-southeast-1.bytepluses.com/api/v3/auc/bigmodel"
    )
    byteplus_asr_resource_id: str = "volc.seedasr.auc"
    byteplus_tts_url: str = (
        "https://voice.ap-southeast-1.bytepluses.com/api/v3/tts/unidirectional"
    )
    byteplus_tts_resource_id: str = "seed-tts-1.0"
    byteplus_tts_voice: str = "en_female_skye_emo_v2_mars_bigtts"

    modelark_api_key: str = ""
    modelark_base_url: str = "https://ark.ap-southeast.bytepluses.com/api/v3"
    main_agent_endpoint: str = ""
    script_endpoint: str = ""
    image_endpoint: str = ""
    video_endpoint: str = ""
    video_review_endpoint: str = ""

    @field_validator("byteplus_tts_voice")
    @classmethod
    def require_american_voice(cls, value: str) -> str:
        normalized = value.lower().replace("-", "_")
        verified_en_us = {
            "en_female_skye_emo_v2_mars_bigtts",
        }
        if not normalized.startswith("en_us") and normalized not in verified_en_us:
            raise ValueError(
                "BYTEPLUS_TTS_VOICE must be a verified en-US voice; "
                "British or non-English fallback is forbidden."
            )
        return value

    @model_validator(mode="after")
    def require_production_session_secret(self) -> "Settings":
        if (
            self.app_env == "production"
            and self.session_secret == "speakbuddy-local-session-secret"
        ):
            raise ValueError("SESSION_SECRET must be set in production")
        return self

    @property
    def ai_enabled(self) -> bool:
        return bool(
            not self.mock_ai and self.modelark_api_key and self.main_agent_endpoint
        )

    @property
    def speech_enabled(self) -> bool:
        return bool(not self.mock_ai and self.speech_api_key)

    @property
    def tos_enabled(self) -> bool:
        return bool(
            not self.mock_ai
            and self.byteplus_ak
            and self.byteplus_sk
            and self.tos_bucket
        )

    @property
    def data_dir(self) -> Path:
        path = Path(self.local_data_dir)
        return path if path.is_absolute() else ROOT / path

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"


@lru_cache
def get_settings() -> Settings:
    return Settings()
