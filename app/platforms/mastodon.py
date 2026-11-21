"""Mastodon integration (works with any Mastodon-compatible instance).

Docs: https://docs.joinmastodon.org/methods/statuses/#create
"""

from __future__ import annotations

from app.platforms.base import BasePlatform, PlatformError, PublishResult


class MastodonPlatform(BasePlatform):
    name = "mastodon"
    display_name = "Mastodon"
    required_settings = ("mastodon_instance", "mastodon_access_token")
    docs_url = "https://docs.joinmastodon.org/methods/statuses/#create"

    async def publish(self, message: str, cta_url: str) -> PublishResult:
        instance = self.settings.mastodon_instance.rstrip("/")
        response = await self.request(
            "POST",
            f"{instance}/api/v1/statuses",
            context=f"{self.display_name} status creation",
            headers={"Authorization": f"Bearer {self.settings.mastodon_access_token}"},
            data={"status": message, "visibility": "public"},
        )

        try:
            status = response.json()
            posted_url = status.get("url") or status.get("uri")
        except ValueError as exc:
            raise PlatformError(
                f"{self.display_name}: unexpected response format"
            ) from exc

        if not posted_url:
            raise PlatformError(
                f"{self.display_name}: status creation response did not contain a URL"
            )

        date, time = self.utc_timestamp()
        return PublishResult(
            platform=self.display_name,
            status="success",
            posted_url=posted_url,
            # The status was requested with public visibility; Mastodon always
            # returns the public URL in the "url" field for public statuses.
            public_access=True,
            date=date,
            time=time,
        )