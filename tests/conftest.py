"""Shared test fixtures."""

import pytest

from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Settings with fake credentials for every platform (no real secrets)."""
    return Settings(
        _env_file=None,
        bluesky_identifier="alice.bsky.social",
        bluesky_app_password="fake-app-password",
        devto_api_key="fake-devto-key",
        mastodon_instance="https://mastodon.social",
        mastodon_access_token="fake-mastodon-token",
        telegram_bot_token="123456:FAKE",
        telegram_chat_id="@test_channel",
        discord_webhook_url="https://discord.com/api/webhooks/123456/fake",
    )