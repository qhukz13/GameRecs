import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Coop Game Recommendations API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/game_recs"
    # Keep as str so pydantic-settings doesn't try to JSON-decode it at the source level.
    # Use settings.get_cors_origins() to get the parsed list.
    cors_origins: str = "http://localhost:3000"
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

    def get_cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS from any format:
        - JSON array:       '["https://a.com","https://b.com"]'
        - Comma-separated:  'https://a.com,https://b.com'
        - Single URL:       'https://a.com'
        """
        raw = (self.cors_origins or "").strip()
        if not raw:
            return ["http://localhost:3000"]
        if raw.startswith("["):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

