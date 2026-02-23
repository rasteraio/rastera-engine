"""
Rastera Engine — Application Settings
All config loaded from environment variables (with .env fallback via pydantic-settings).
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+psycopg://rastera:CHANGE_ME@db:5432/rastera"

    # ── OpenAI ────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1-mini"
    AI_ENABLED: bool = True

    # ── CORS ──────────────────────────────────────────────────────────────
    # Comma-separated list; split at runtime
    ALLOWED_ORIGINS: str = (
        "https://rastera.io,https://www.rastera.io,http://localhost:3000"
    )

    # ── App ───────────────────────────────────────────────────────────────
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
