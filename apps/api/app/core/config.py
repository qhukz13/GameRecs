from functools import lru_cache

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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

