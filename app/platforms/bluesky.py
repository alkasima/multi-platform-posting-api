"""Bluesky (AT Protocol) integration.

Docs: https://docs.bsky.app/docs/advanced-guides/posts
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.platforms.base import BasePlatform, PlatformError, PublishResult


class BlueskyPlatform(BasePlatform):
    name = "bluesky"
    display_name = "Bluesky"
    required_settings = ("bluesky_identifier", "bluesky_app_password")
    docs_url = "https://docs.bsky.app/docs/advanced-guides/posts"

    BASE_URL = "https://bsky.social/xrpc"

    async def publish(self, message: str, cta_url: str) -> PublishResult:
        # 1. Authenticate (app password, not the account password).
        session_response = await self.request(
            "POST",
            f"{self.BASE_URL}/com.atproto.server.createSession",
            context=f"{self.display_name} authentication",
            json={
                "identifier": self.settings.bluesky_identifier,
                "password": self.settings.bluesky_app_password,
            },
        )

        try:
            session = session_response.json()
            access_jwt = session["accessJwt"]
            did = session["did"]
            handle = session.get("handle", self.settings.bluesky_identifier)
        except (ValueError, KeyError) as exc:
            raise PlatformError(
                f"{self.display_name}: unexpected authentication response"
            ) from exc

        # 2. Create the post record.
        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        }
        record_response = await self.request(
            "POST",
            f"{self.BASE_URL}/com.atproto.repo.createRecord",
            context=f"{self.display_name} post creation",
            headers={"Authorization": f"Bearer {access_jwt}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
        )

        try:
            uri = record_response.json()["uri"]
        except (ValueError, KeyError) as exc:
            raise PlatformError(
                f"{self.display_name}: post creation response did not contain a URI"
            ) from exc

        rkey = uri.rstrip("/").rsplit("/", 1)[-1]
        date, time = self.utc_timestamp()
        return PublishResult(
            platform=self.display_name,
            status="success",
            posted_url=f"https://bsky.app/profile/{handle}/post/{rkey}",
            public_access=True,
            date=date,
            time=time,
        )