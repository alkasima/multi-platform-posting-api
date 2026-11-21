"""Shared helpers for HTTP mocking in tests."""

import httpx
import respx

BLUESKY_SESSION = "https://bsky.social/xrpc/com.atproto.server.createSession"
BLUESKY_RECORD = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
DEVTO_ARTICLES = "https://dev.to/api/articles"
MASTODON_STATUSES = "https://mastodon.social/api/v1/statuses"
TELEGRAM_MESSAGE = "https://api.telegram.org/bot123456:FAKE/sendMessage"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/123456/fake?wait=true"


def mock_all_platforms(*, devto_status: int = 201) -> None:
    """Register successful responses for every platform.

    ``devto_status`` can be used to simulate a single platform failing.
    """
    respx.post(BLUESKY_SESSION).mock(
        return_value=httpx.Response(
            200,
            json={
                "accessJwt": "jwt",
                "did": "did:plc:abc",
                "handle": "alice.bsky.social",
            },
        )
    )
    respx.post(BLUESKY_RECORD).mock(
        return_value=httpx.Response(
            200, json={"uri": "at://did:plc:abc/app.bsky.feed.post/1", "cid": "x"}
        )
    )
    respx.post(DEVTO_ARTICLES).mock(
        return_value=httpx.Response(
            devto_status,
            json=(
                {"url": "https://dev.to/alice/post"}
                if devto_status < 400
                else {"error": "unauthorized"}
            ),
        )
    )
    respx.post(MASTODON_STATUSES).mock(
        return_value=httpx.Response(
            200, json={"url": "https://mastodon.social/@alice/1"}
        )
    )
    respx.post(TELEGRAM_MESSAGE).mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "result": {"message_id": 1, "chat": {"id": 1, "username": "ch"}},
            },
        )
    )
    respx.post(DISCORD_WEBHOOK).mock(
        return_value=httpx.Response(
            200, json={"id": "1", "channel_id": "2", "guild_id": "3"}
        )
    )