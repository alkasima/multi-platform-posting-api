"""End-to-end tests for the FastAPI application (in-process, no network)."""

import httpx
import pytest
import respx

from app.config import get_settings
from app.main import app, get_posting_service
from app.services.posting_service import PostingService

from tests.helpers import mock_all_platforms

MESSAGE = (
    "Check out our latest business platform and grow your online visibility. "
    "https://example.com"
)


@pytest.fixture
def client(settings):
    """ASGI client whose posting service uses fake test credentials."""
    app.dependency_overrides[get_posting_service] = lambda: PostingService(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.clear()


async def _post(client, payload):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        return await http.post("/posting", json=payload)


async def test_health_endpoint(client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        response = await http.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_platforms_endpoint(client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        response = await http.get("/platforms")

    assert response.status_code == 200
    platforms = response.json()["platforms"]
    assert len(platforms) == 5
    assert all(item["configured"] for item in platforms)


@respx.mock
async def test_posting_success(client):
    mock_all_platforms()

    response = await _post(client, {"message": MESSAGE})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["results"]) == 5
    for result in body["results"]:
        assert set(result) == {
            "platform",
            "status",
            "posted_url",
            "public_access",
            "date",
            "time",
            "error",
        }
        assert result["status"] == "success"
        assert result["error"] is None
        assert result["date"] and result["time"]


@respx.mock
async def test_posting_partial_failure(client):
    mock_all_platforms(devto_status=403)

    response = await _post(client, {"message": MESSAGE})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    failed = [r for r in body["results"] if r["status"] == "failed"]
    assert len(failed) == 1
    assert failed[0]["platform"] == "DEV Community"
    assert "HTTP 403" in failed[0]["error"]


async def test_posting_rejects_invalid_message(client):
    response = await _post(client, {"message": "No link in this message"})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "validation_error"
    assert any("exactly one CTA link" in item["message"] for item in body["details"])


async def test_posting_rejects_long_message(client):
    response = await _post(
        client, {"message": "a" * 201 + " https://example.com"}
    )

    assert response.status_code == 422
    body = response.json()
    assert any("200 characters" in item["message"] for item in body["details"])


async def test_openapi_schema_is_served(client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        response = await http.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/posting" in schema["paths"]
    assert "PostResponse" in schema["components"]["schemas"]