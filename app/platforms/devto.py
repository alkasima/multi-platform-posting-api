"""DEV Community (dev.to) integration.

Docs: https://developers.forem.com/api/v1#operation/createArticle
"""

from __future__ import annotations

from app.platforms.base import BasePlatform, PlatformError, PublishResult


class DevToPlatform(BasePlatform):
    name = "devto"
    display_name = "DEV Community"
    required_settings = ("devto_api_key",)
    docs_url = "https://developers.forem.com/api/v1#operation/createArticle"

    API_URL = "https://dev.to/api/articles"

    async def publish(self, message: str, cta_url: str) -> PublishResult:
        response = await self.request(
            "POST",
            self.API_URL,
            context=f"{self.display_name} article creation",
            headers={"api-key": self.settings.devto_api_key},
            json={
                "title": self.make_title(message, cta_url),
                "body_markdown": message,
                "published": True,
            },
        )

        try:
            article = response.json()
            posted_url = article["url"]
        except (ValueError, KeyError, TypeError) as exc:
            raise PlatformError(
                f"{self.display_name}: article creation response did not contain a URL"
            ) from exc

        if not posted_url:
            raise PlatformError(
                f"{self.display_name}: article creation response did not contain a URL"
            )

        date, time = self.utc_timestamp()
        return PublishResult(
            platform=self.display_name,
            status="success",
            posted_url=posted_url,
            public_access=True,
            date=date,
            time=time,
        )