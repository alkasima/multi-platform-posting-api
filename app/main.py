"""FastAPI application entry point.

Run locally with::

    uvicorn app.main:app --host 0.0.0.0 --port 4000
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import Settings, get_settings
from app.schemas import PlatformResult, PostRequest, PostResponse
from app.services.posting_service import PostingService, describe_platforms

logger = logging.getLogger("posting")

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

    @application.get("/", include_in_schema=False, response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(
            """
            <!doctype html>
            <html lang="en">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title>Automated Multi-Platform Posting System</title>
              <style>
                body { font-family: system-ui, "Segoe UI", Arial, sans-serif;
                       max-width: 820px; margin: 48px auto; padding: 0 20px;
                       color: #18181b; line-height: 1.5; }
                h1 { margin-bottom: .25rem; }
                p.lead { color: #52525b; margin-top: 0; }
                nav a { margin-right: 1rem; }
                .card { border: 1px solid #e4e4e7; border-radius: 10px;
                        padding: 18px; margin-top: 1.5rem; background: #fff; }
                label { display: block; font-weight: 600; margin-bottom: .35rem; }
                textarea { width: 100%; box-sizing: border-box; font: inherit;
                           padding: 10px; border: 1px solid #d4d4d8;
                           border-radius: 8px; resize: vertical; }
                button { margin-top: .75rem; padding: 9px 16px; font: inherit;
                         font-weight: 600; border: 0; border-radius: 8px;
                         background: #18181b; color: #fff; cursor: pointer; }
                button:hover { background: #3f3f46; }
                pre { background: #f4f4f5; border-radius: 8px; padding: 14px;
                      overflow: auto; font-size: .85rem; max-height: 420px; }
                .hint { color: #71717a; font-size: .85rem; }
              </style>
            </head>
            <body>
              <h1>Automated Multi-Platform Posting System</h1>
              <p class="lead">One endpoint that publishes a message to several
                 third-party platforms independently and reports the result for each.</p>

              <nav>
                <a href="/docs">API docs (Swagger UI)</a>
                <a href="/redoc">ReDoc</a>
                <a href="/openapi.json">OpenAPI schema</a>
                <a href="/platforms">Platform status</a>
                <a href="/health">Health</a>
              </nav>

              <div class="card">
                <h2>Try it</h2>
                <form id="demo-form">
                  <label for="message">Message (max 200 characters, exactly one link)</label>
                  <textarea id="message" rows="3">Check out our latest business platform and grow your online visibility. https://example.com</textarea>
                  <button type="submit">Post to all platforms</button>
                </form>
                <p class="hint">Without credentials every platform reports a
                   configuration error; with <code>DEMO_MODE=true</code> the
                   results are simulated and labelled accordingly.</p>
                <pre id="output">Submit the form to see the JSON response.</pre>
              </div>

              <script>
                const form = document.getElementById("demo-form");
                const output = document.getElementById("output");
                form.addEventListener("submit", async (event) => {
                  event.preventDefault();
                  const message = document.getElementById("message").value;
                  output.textContent = "Posting...";
                  try {
                    const response = await fetch("/posting", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ message }),
                    });
                    output.textContent = JSON.stringify(
                      await response.json(), null, 2
                    );
                  } catch (error) {
                    output.textContent = String(error);
                  }
                });
              </script>
            </body>
            </html>
            """
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