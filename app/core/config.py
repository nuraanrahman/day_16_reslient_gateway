from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- OpenAI ---
    openai_api_key: str = ""
    default_model: str = "gpt-4o-mini"

    # --- Anthropic ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # --- App ---
    environment: str = "dev"
    log_level: str = "INFO"

    # --- CORS ---
    cors_origins: str = "*"

    # --- JWT ---
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
