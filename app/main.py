"""FastAPI application entry point.

Run locally with::

    uvicorn app.main:app --host 0.0.0.0 --port 4000
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.schemas import PlatformResult, PostRequest, PostResponse
from app.services.posting_service import PostingService, describe_platforms

logger = logging.getLogger("posting")

STATIC_DIR = Path(__file__).resolve().parent / "static"

DESCRIPTION = """
Automatically publish one short message to multiple third-party platforms.

* **Validates** the message (max 200 characters, exactly one CTA link).
* **Posts independently** to every configured platform and keeps going if one fails.
* **Reports** status, URL, public access, date, time and error per platform.

Platform credentials are read from environment variables; see `.env.example`.
"""


def get_posting_service(settings: Settings = Depends(get_settings)) -> PostingService:
    """Dependency that builds a :class:`PostingService` from current settings."""
    return PostingService(settings)


def create_app() -> FastAPI:
    """Build the FastAPI application (kept as a function so tests can rebuild it)."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
    )

    application.mount(
        "/static", StaticFiles(directory=STATIC_DIR), name="static"
    )

    @application.get("/", include_in_schema=False, response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(
            (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        )

    @application.get("/health", summary="Health check")
    async def health(settings: Settings = Depends(get_settings)) -> dict:
        return {
            "status": "ok",
            "version": settings.app_version,
            "demo_mode": settings.demo_mode,
        }

    @application.get("/platforms", summary="List platforms and their configuration status")
    async def platforms(settings: Settings = Depends(get_settings)) -> dict:
        return {"platforms": describe_platforms(settings)}

    @application.post(
        "/posting",
        response_model=PostResponse,
        summary="Publish a message to all configured platforms",
    )
    async def publish_message(
        payload: PostRequest,
        service: PostingService = Depends(get_posting_service),
    ) -> PostResponse:
        results = await service.publish(payload.message, payload.cta_url)
        return PostResponse(
            success=any(result.status == "success" for result in results),
            results=[PlatformResult(**result.to_dict()) for result in results],
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return a compact, documented 422 payload for invalid input."""
        details = []
        for error in exc.errors():
            location = ".".join(
                str(part) for part in error.get("loc", ()) if part != "body"
            )
            details.append(
                {
                    "field": location or "body",
                    "message": error.get("msg", "Invalid value"),
                    "type": error.get("type", "value_error"),
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": "validation_error",
                "details": details,
            },
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled error while processing %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "internal_server_error",
                "message": "An unexpected error occurred.",
            },
        )

    return application


app = create_app()