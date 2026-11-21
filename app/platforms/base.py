"""Base class shared by every platform integration."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.config import Settings


class PlatformError(Exception):
    """Raised when a platform integration fails."""


@dataclass
class PublishResult:
    """Internal, framework-agnostic publishing result."""

    platform: str
    status: str
    posted_url: Optional[str] = None
    public_access: bool = False
    date: Optional[str] = None
    time: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BasePlatform(ABC):
    """Every integration implements :meth:`publish`.

    A subclass declares its ``display_name``, the settings it needs and its
    public API documentation URL. The base class takes care of configuration
    checks, request timeouts, error wrapping and timestamps.
    """

    name: str = "base"
    display_name: str = "Base"
    required_settings: tuple[str, ...] = ()
    docs_url: str = ""

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    # -- configuration ------------------------------------------------------
    def missing_settings(self) -> list[str]:
        """Return the names of settings that are not configured."""
        return [
            key.upper()
            for key in self.required_settings
            if not getattr(self.settings, key, "")
        ]

    @property
    def is_configured(self) -> bool:
        return not self.missing_settings()

    # -- interface ----------------------------------------------------------
    @abstractmethod
    async def publish(self, message: str, cta_url: str) -> PublishResult:
        """Publish ``message`` and return the result for this platform."""

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def utc_timestamp() -> tuple[str, str]:
        """Return the current UTC date and time as ``(date, time)`` strings."""
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    async def request(
        self,
        method: str,
        url: str,
        *,
        context: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform an HTTP request and turn failures into ``PlatformError``."""
        try:
            response = await self.client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise PlatformError(
                f"{context}: request failed ({type(exc).__name__}: {exc})"
            ) from exc

        if response.status_code >= 400:
            raise PlatformError(
                f"{context}: HTTP {response.status_code} - {self._short(response.text)}"
            )
        return response

    @staticmethod
    def _short(text: str, limit: int = 300) -> str:
        """Collapse whitespace and truncate a response body for error messages."""
        text = " ".join((text or "").split())
        return text[:limit] or "<empty response>"

    @staticmethod
    def make_title(message: str, cta_url: str, max_length: int = 60) -> str:
        """Build a short post title from the message (URL removed)."""
        text = message.replace(cta_url, " ")
        text = re.sub(r"\s+", " ", text).strip(" -–—:|")
        if not text:
            return "Automated post"
        if len(text) <= max_length:
            return text
        shortened = text[:max_length].rsplit(" ", 1)[0].strip(" -–—:|,")
        return shortened or text[:max_length]