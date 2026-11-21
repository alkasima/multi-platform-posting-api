"""Simulated platform used only when ``DEMO_MODE=true``.

It performs no network calls and labels every result "(simulated)" so a demo
response can never be mistaken for a real integration.
"""

from __future__ import annotations

import re
from uuid import uuid4

import httpx

from app.config import Settings
from app.platforms.base import BasePlatform, PublishResult


def _slugify(value: str, max_length: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:max_length].rstrip("-") or "post"


class SimulatedPlatform(BasePlatform):
    """Stand-in for one real platform during a demo run."""

    def __init__(
        self, settings: Settings, client: httpx.AsyncClient, source_name: str
    ) -> None:
        super().__init__(settings, client)
        self.source_name = source_name
        self.display_name = f"{source_name} (simulated)"
        self.name = f"simulated_{_slugify(source_name).replace('-', '_')}"

    async def publish(self, message: str, cta_url: str) -> PublishResult:
        date, time = self.utc_timestamp()
        platform_slug = _slugify(self.source_name)
        message_slug = _slugify(message, 50)
        return PublishResult(
            platform=self.display_name,
            status="success",
            posted_url=(
                f"https://example.com/simulated/{platform_slug}/"
                f"{message_slug}-{uuid4().hex[:6]}"
            ),
            public_access=True,
            date=date,
            time=time,
        )