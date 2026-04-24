"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings bound to .env.

    We use pydantic-settings so missing or mistyped env vars fail fast at
    startup instead of producing obscure errors deep inside a request.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required credentials for the Copernicus Data Space Ecosystem OAuth client.
    cdse_client_id: str
    cdse_client_secret: str

    # CDSE endpoints. Kept in config (with defaults) so they can be overridden
    # per environment without code changes.
    cdse_token_url: str = (
        "https://identity.dataspace.copernicus.eu/auth/realms/"
        "CDSE/protocol/openid-connect/token"
    )
    cdse_process_url: str = "https://sh.dataspace.copernicus.eu/api/v1/process"

    # Frontend origin used by the CORS middleware (Vite default in dev).
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    lru_cache ensures .env is parsed exactly once per process, which is what
    FastAPI's dependency system expects for configuration.
    """
    return Settings()