import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Coop Game Recommendations API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/game_recs"
    cors_origins: list[str] = ["http://localhost:3000"]
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    embedding_dim: int = 8
    recommendation_limit: int = 5
    # AI provider settings
    ai_provider: str = "local"  # options: local, ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Accept CORS_ORIGINS in any format:
        - JSON array:        '["https://a.com","https://b.com"]'
        - Comma-separated:   'https://a.com,https://b.com'
        - Single URL:        'https://a.com'
        - Already a list:    ["https://a.com"]
        """
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # comma-separated or single value
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

