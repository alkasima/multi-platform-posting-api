"""Validation rules for POST /posting."""

import pytest
from pydantic import ValidationError

from app.schemas import PostRequest

VALID_MESSAGE = (
    "Check out our latest business platform and grow your online visibility. "
    "https://example.com"
)


def test_valid_message_is_accepted():
    request = PostRequest(message=VALID_MESSAGE)
    assert request.cta_url == "https://example.com"


def test_message_is_trimmed():
    request = PostRequest(message=f"  {VALID_MESSAGE}  ")
    assert request.message == VALID_MESSAGE


def test_url_with_trailing_punctuation_is_normalized():
    request = PostRequest(message="Read more at https://example.com/post.")
    assert request.cta_url == "https://example.com/post"


@pytest.mark.parametrize(
    "message",
    [
        "This message has no link at all.",
        "Two links https://example.com and https://example.org",
        "",
        "     ",
        "x" * 201 + " https://example.com",
    ],
)
def test_invalid_messages_are_rejected(message):
    with pytest.raises(ValidationError):
        PostRequest(message=message)


@pytest.mark.parametrize(
    "message",
    [
        "Try ftp://example.com/file",
        "Try javascript:alert(1)",
        "Try https://",
        "Try https://localhost/page",
        "Try https://user:pass@example.com/",
    ],
)
def test_invalid_urls_are_rejected(message):
    with pytest.raises(ValidationError):
        PostRequest(message=message)


def test_message_with_exactly_one_link_and_http_scheme_is_valid():
    request = PostRequest(message="Visit http://example.co.uk/page for details")
    assert request.cta_url == "http://example.co.uk/page"


def test_message_length_boundary():
    # Exactly 200 characters including the URL.
    prefix = "a" * (200 - len(" https://example.com"))
    request = PostRequest(message=f"{prefix} https://example.com")
    assert len(request.message) == 200