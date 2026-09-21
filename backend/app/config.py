from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Default to SQLite for local dev without Docker/PostgreSQL.
    # Use PostgreSQL in production via DATABASE_URL env var or docker-compose.
    database_url: str = "sqlite+aiosqlite:///./evidencelens.db"
    database_url_sync: str = "sqlite:///./evidencelens.db"
    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 25
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def uses_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
