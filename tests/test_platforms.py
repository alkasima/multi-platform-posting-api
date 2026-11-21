"""Unit tests for each platform integration (all HTTP calls are mocked)."""

import json

import httpx
import pytest
import respx

from app.platforms.base import PlatformError
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.telegram import TelegramPlatform

MESSAGE = "Check out our platform and grow: https://example.com"
CTA_URL = "https://example.com"


@respx.mock
async def test_bluesky_publish(settings):
    respx.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "accessJwt": "jwt-token",
                "did": "did:plc:abc123",
                "handle": "alice.bsky.social",
            },
        )
    )
    respx.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"uri": "at://did:plc:abc123/app.bsky.feed.post/3k4abc", "cid": "bafy"},
        )
    )

    async with httpx.AsyncClient() as client:
        result = await BlueskyPlatform(settings, client).publish(MESSAGE, CTA_URL)

    assert result.status == "success"
    assert result.platform == "Bluesky"
    assert result.posted_url == (
        "https://bsky.app/profile/alice.bsky.social/post/3k4abc"
    )
    assert result.public_access is True
    assert result.date and result.time


@respx.mock
async def test_devto_publish(settings):
    route = respx.post("https://dev.to/api/articles").mock(
        return_value=httpx.Response(201, json={"url": "https://dev.to/alice/post"})
    )

    async with httpx.AsyncClient() as client:
        result = await DevToPlatform(settings, client).publish(MESSAGE, CTA_URL)

    assert result.status == "success"
    assert result.posted_url == "https://dev.to/alice/post"
    request = route.calls.last.request
    assert request.headers["api-key"] == "fake-devto-key"
    body = json.loads(request.content)
    assert body["article"]["body_markdown"] == MESSAGE
    assert body["article"]["published"] is True
    assert body["article"]["title"]


@respx.mock
async def test_mastodon_publish(settings):
    respx.post("https://mastodon.social/api/v1/statuses").mock(
        return_value=httpx.Response(
            200,
            json={"url": "https://mastodon.social/@alice/123", "uri": "tag:..."},
        )
    )

    async with httpx.AsyncClient() as client:
        result = await MastodonPlatform(settings, client).publish(MESSAGE, CTA_URL)

    assert result.status == "success"
    assert result.posted_url == "https://mastodon.social/@alice/123"
    assert result.public_access is True


@respx.mock
async def test_telegram_public_channel(settings):
    respx.post(
        "https://api.telegram.org/bot123456:FAKE/sendMessage"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "message_id": 42,
                    "chat": {"id": -1001234567890, "username": "test_channel"},
                },
            },
        )
    )

    async with httpx.AsyncClient() as client:
        result = await TelegramPlatform(settings, client).publish(MESSAGE, CTA_URL)

    assert result.status == "success"
    assert result.posted_url == "https://t.me/test_channel/42"
    assert result.public_access is True


@respx.mock
async def test_telegram_private_chat_is_not_public(settings):
    respx.post(
        "https://api.telegram.org/bot123456:FAKE/sendMessage"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "message_id": 7,
                    "chat": {"id": -1001234567890, "type": "group"},
                },
            },
        )
    )

    async with httpx.AsyncClient() as client:
        result = await TelegramPlatform(settings, client).publish(MESSAGE, CTA_URL)

    assert result.status == "success"
    assert result.public_access is False
    assert result.posted_url == "https://t.me/c/1234567890/7"


@respx.mock
async def test_discord_publish(settings):
    respx.post(
        "https://discord.com/api/webhooks/123456/fake?wait=true"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "999",
                "channel_id": "111",
                "guild_id": "222",
            },
        )
    )

    async with httpx.AsyncClient() as client:
        result = await DiscordPlatform(settings, client).publish(MESSAGE, CTA_URL)

    assert result.status == "success"
    assert result.posted_url == "https://discord.com/channels/222/111/999"
    assert result.public_access is False


@respx.mock
async def test_bluesky_authentication_failure_raises(settings):
    respx.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession"
    ).mock(return_value=httpx.Response(401, text="Authentication Required"))

    async with httpx.AsyncClient() as client:
        with pytest.raises(PlatformError) as excinfo:
            await BlueskyPlatform(settings, client).publish(MESSAGE, CTA_URL)

    assert "HTTP 401" in str(excinfo.value)