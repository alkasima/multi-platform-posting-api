"""Tests for the multi-platform orchestration service."""

import respx

from app.config import Settings
from app.services.posting_service import PostingService, describe_platforms
from tests.helpers import mock_all_platforms

MESSAGE = "Check out our platform and grow: https://example.com"
CTA_URL = "https://example.com"


@respx.mock
async def test_all_platforms_succeed(settings):
    mock_all_platforms()

    results = await PostingService(settings).publish(MESSAGE, CTA_URL)

    assert len(results) == 5
    assert all(result.status == "success" for result in results)
    assert {result.platform for result in results} == {
        "Bluesky",
        "DEV Community",
        "Mastodon",
        "Telegram",
        "Discord",
    }


@respx.mock
async def test_one_failure_does_not_stop_the_others(settings):
    mock_all_platforms(devto_status=401)

    results = await PostingService(settings).publish(MESSAGE, CTA_URL)

    statuses = {result.platform: result.status for result in results}
    assert statuses["DEV Community"] == "failed"
    assert sum(1 for result in results if result.status == "success") == 4

    devto = next(r for r in results if r.platform == "DEV Community")
    assert "HTTP 401" in (devto.error or "")


async def test_unconfigured_platforms_fail_with_a_clear_error():
    settings = Settings(_env_file=None)

    results = await PostingService(settings).publish(MESSAGE, CTA_URL)

    assert len(results) == 5
    assert all(result.status == "failed" for result in results)
    assert all(
        "Missing configuration" in (result.error or "") for result in results
    )


async def test_demo_mode_simulates_every_platform(settings):
    settings = Settings(_env_file=None, demo_mode=True)

    results = await PostingService(settings).publish(MESSAGE, CTA_URL)

    assert len(results) == 5
    assert all(result.status == "success" for result in results)
    assert all("(simulated)" in result.platform for result in results)
    assert all(result.posted_url for result in results)


def test_describe_platforms_reports_configuration(settings):
    description = describe_platforms(settings)
    assert len(description) == 5
    assert all(item["configured"] for item in description)
    assert all(item["docs"] for item in description)
    assert all(item["simulated"] is False for item in description)


def test_describe_platforms_reports_missing_settings():
    description = describe_platforms(Settings(_env_file=None))
    assert all(not item["configured"] for item in description)
    bluesky = next(item for item in description if item["platform"] == "Bluesky")
    assert bluesky["missing_settings"] == [
        "BLUESKY_IDENTIFIER",
        "BLUESKY_APP_PASSWORD",
    ]