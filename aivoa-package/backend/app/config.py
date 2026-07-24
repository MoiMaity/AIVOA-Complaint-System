"""Application settings, loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App -------------------------------------------------------------
    app_name: str = "AIVOA Complaint Management API"
    environment: str = "development"
    api_prefix: str = "/api"

    # Comma-separated list of origins allowed to call this API.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Database --------------------------------------------------------
    # Postgres (default):
    #   postgresql+psycopg2://aivoa:aivoa@localhost:5432/aivoa_complaints
    # MySQL:
    #   mysql+pymysql://aivoa:aivoa@localhost:3306/aivoa_complaints
    database_url: str = (
        "postgresql+psycopg2://aivoa:aivoa@localhost:5432/aivoa_complaints"
    )

    # --- Groq / LLM ------------------------------------------------------
    groq_api_key: str = ""
    # Primary extraction model required by the assessment.
    groq_model: str = "gemma2-9b-it"
    # Larger model for reasoning-heavy nodes (risk, CAPA, chat).
    groq_reasoning_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_timeout_seconds: float = 45.0
    groq_max_retries: int = 2

    # --- Uploads ---------------------------------------------------------
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB, matches the UI copy

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        """False when no key is set — the app then runs in offline demo mode."""
        return bool(self.groq_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
