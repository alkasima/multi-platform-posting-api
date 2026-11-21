"""Application configuration.

All credentials are read from environment variables (or a local ``.env`` file)
so that no secret ever has to be committed to the repository.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings object loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General -----------------------------------------------------------------
    app_name: str = "Automated Multi-Platform Posting System"
    app_version: str = "1.0.0"
    request_timeout: float = 15.0
    # When true, every platform is replaced by a clearly-labelled simulation
    # so the API can be demonstrated end-to-end without real credentials.
    demo_mode: bool = False

    # Bluesky -----------------------------------------------------------------
    bluesky_identifier: str = ""
    bluesky_app_password: str = ""

    # DEV Community (dev.to) --------------------------------------------------
    devto_api_key: str = ""

    # Mastodon ----------------------------------------------------------------
    mastodon_instance: str = "https://mastodon.social"
    mastodon_access_token: str = ""

    # Telegram ----------------------------------------------------------------
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Discord -----------------------------------------------------------------
    discord_webhook_url: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()