"""Service that fans a message out to every configured platform."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.config import Settings
from app.platforms.base import BasePlatform, PlatformError, PublishResult
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.simulated import SimulatedPlatform
from app.platforms.telegram import TelegramPlatform

#: Real integrations, executed in this order.
PLATFORM_CLASSES: tuple[type[BasePlatform], ...] = (
    BlueskyPlatform,
    DevToPlatform,
    MastodonPlatform,
    TelegramPlatform,
    DiscordPlatform,
)


def get_platform_instances(
    settings: Settings, client: httpx.AsyncClient
) -> list[BasePlatform]:
    """Build platform instances, using simulations when ``DEMO_MODE`` is on."""
    if settings.demo_mode:
        return [
            SimulatedPlatform(settings, client, cls.display_name)
            for cls in PLATFORM_CLASSES
        ]
    return [cls(settings, client) for cls in PLATFORM_CLASSES]


def describe_platforms(settings: Settings) -> list[dict[str, Any]]:
    """Describe every platform and whether it is configured (no network calls)."""
    description: list[dict[str, Any]] = []
    for cls in PLATFORM_CLASSES:
        missing = [
            key.upper()
            for key in cls.required_settings
            if not getattr(settings, key, "")
        ]
        description.append(
            {
                "platform": cls.display_name,
                "configured": not missing,
                "required_settings": [key.upper() for key in cls.required_settings],
                "missing_settings": missing,
                "docs": cls.docs_url,
                "simulated": settings.demo_mode,
            }
        )
    return description


class PostingService:
    """Publishes one message to all platforms, independently."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def publish(self, message: str, cta_url: str) -> list[PublishResult]:
        """Publish ``message`` everywhere and always return one result per platform."""
        timeout = httpx.Timeout(self.settings.request_timeout)
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": f"{self.settings.app_name}/{self.settings.app_version}"},
        ) as client:
            platforms = get_platform_instances(self.settings, client)
            return list(
                await asyncio.gather(
                    *(self._publish_one(p, message, cta_url) for p in platforms)
                )
            )

    async def _publish_one(
        self, platform: BasePlatform, message: str, cta_url: str
    ) -> PublishResult:
        missing = platform.missing_settings()
        if missing:
            return self._failure(
                platform, f"Missing configuration: {', '.join(missing)}"
            )
        try:
            return await platform.publish(message, cta_url)
        except PlatformError as exc:
            return self._failure(platform, str(exc))
        except Exception as exc:  # noqa: BLE001 - one platform must not stop the rest
            return self._failure(
                platform, f"Unexpected error ({type(exc).__name__}): {exc}"
            )

    @staticmethod
    def _failure(platform: BasePlatform, message: str) -> PublishResult:
        return PublishResult(
            platform=platform.display_name,
            status="failed",
            error=message,
        )