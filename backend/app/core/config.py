"""
Candor — Application settings.

Loaded from environment variables / .env file.
Temperature 0 is enforced in the agent module — not here — but
confidence_threshold lives here so it can be read at startup and
overridden from the DB at runtime.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Look in parent directory first (repo root .env), then current dir
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Gemini
    gemini_api_key: str

    # Matching — also stored and updated in the config DB table
    confidence_threshold: float = 0.75

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
