"""Request/response schemas and input validation rules."""

from __future__ import annotations

import ipaddress
import re
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_LENGTH = 200

# A CTA link is any http(s) URL embedded in the message.
URL_PATTERN = re.compile(r"https?://[^\s<>\"'`]+", re.IGNORECASE)

# Punctuation that commonly trails a URL inside prose ("...example.com.").
_TRAILING_PUNCTUATION = ".,;:!?)]}\"'"


def extract_links(text: str) -> list[str]:
    """Return every http(s) URL found in ``text``."""
    return URL_PATTERN.findall(text or "")


def normalize_link(url: str) -> str:
    """Strip trailing prose punctuation from a matched URL."""
    return url.rstrip(_TRAILING_PUNCTUATION)


def validate_url(url: str) -> None:
    """Raise ``ValueError`` if ``url`` is not a usable public http(s) URL."""
    try:
        parsed = urlparse(url)
    except ValueError as exc:  # pragma: no cover - urlparse rarely raises
        raise ValueError(f"invalid URL: {url!r}") from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("URL must start with http:// or https://")

    if not parsed.netloc or not parsed.hostname:
        raise ValueError("URL must include a host, e.g. https://example.com")

    if parsed.username or parsed.password:
        raise ValueError("URL must not contain embedded credentials")

    if any(char.isspace() for char in url):
        raise ValueError("URL must not contain whitespace")

    hostname = parsed.hostname or ""

    # Allow bare IP addresses, but require a dot for normal hostnames so that
    # values such as "https://localhost" or "https://intranet" are rejected.
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        if "." not in hostname:
            raise ValueError(
                f"URL host {hostname!r} is not a valid public domain name"
            ) from None


class PostRequest(BaseModel):
    """Body of ``POST /posting``."""

    message: str = Field(
        ...,
        description=(
            "Message to publish. Maximum 200 characters and it must contain "
            "exactly one CTA link."
        ),
        examples=[
            "Check out our latest business platform and grow your online "
            "visibility. https://example.com"
        ],
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        message = value.strip()

        if not message:
            raise ValueError("message must not be empty")

        if len(message) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"message must not exceed {MAX_MESSAGE_LENGTH} characters "
                f"(got {len(message)})"
            )

        links = extract_links(message)
        if len(links) != 1:
            raise ValueError(
                "message must contain exactly one CTA link "
                f"(found {len(links)})"
            )

        validate_url(normalize_link(links[0]))
        return message

    @property
    def cta_url(self) -> str:
        """The single CTA link contained in the message."""
        return normalize_link(extract_links(self.message)[0])


class PlatformResult(BaseModel):
    """Publishing result for one platform."""

    platform: str = Field(examples=["Bluesky"])
    status: Literal["success", "failed"] = Field(examples=["success"])
    posted_url: Optional[str] = Field(
        default=None, examples=["https://bsky.app/profile/alice/post/3k4abc"]
    )
    public_access: bool = Field(
        default=False,
        description="True when the published content is reachable without login.",
    )
    date: Optional[str] = Field(default=None, examples=["2026-11-21"])
    time: Optional[str] = Field(default=None, examples=["10:30:00"])
    error: Optional[str] = Field(
        default=None, examples=["Authentication failed: HTTP 401"]
    )


class PostResponse(BaseModel):
    """Body returned by ``POST /posting``."""

    success: bool = Field(
        description="True when at least one platform accepted the message."
    )
    results: list[PlatformResult]