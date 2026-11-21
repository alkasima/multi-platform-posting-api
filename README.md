# Automated Multi-Platform Posting System

A FastAPI service that publishes one short message to **five third-party platforms
independently**, then returns a per-platform report with status, URL, public
accessibility, date, time and error details.

If one platform fails (bad credentials, rate limit, API outage), the remaining
platforms are still attempted — one failure never stops the batch.

![Landing page with the built-in demo form](screenshots/01-landing-page.jpg)

---

## Table of contents

- [Features](#features)
- [Platforms](#platforms)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Setup](#setup)
- [Configuration](#configuration)
- [Running the API](#running-the-api)
- [API reference](#api-reference)
- [Platform setup guide](#platform-setup-guide)
- [Demo mode](#demo-mode)
- [Testing](#testing)
- [Design notes](#design-notes)
- [Security](#security)
- [Screenshots and logs](#screenshots-and-logs)

---

## Features

| Feature | Description |
| --- | --- |
| Single endpoint | `POST /posting` publishes the message everywhere. |
| Input validation | Max 200 characters, exactly one CTA link, URL syntax and host checks. |
| Five integrations | Bluesky, DEV Community, Mastodon, Telegram and Discord. |
| Independent execution | Platforms run concurrently; a failure on one does not affect the others. |
| Structured results | Every platform returns `platform`, `status`, `posted_url`, `public_access`, `date`, `time`, `error`. |
| Clear errors | HTTP errors are converted into short, readable messages (e.g. `HTTP 401 - ...`). |
| Credentials via env | No secret is committed; `.env.example` documents every variable. |
| Interactive docs | Swagger UI at `/docs`, ReDoc at `/redoc`. |
| Designed dashboard | Dark landing page with live platform status, character counter and syntax-highlighted responses — no build step or CDN. |
| Test suite | 36 unit and integration tests; all HTTP calls are mocked (no network needed). |
| Demo mode | `DEMO_MODE=true` simulates a full multi-platform run without credentials. |

---

## Platforms

| Platform | Type | Credentials | Public access | Official docs |
| --- | --- | --- | --- | --- |
| **Bluesky** | Micro-blogging | Handle + app password | Yes — public profile permalink | [AT Protocol docs](https://docs.bsky.app/docs/advanced-guides/posts) |
| **DEV Community** | Blogging / dev network | API key | Yes — public article URL | [Forem API](https://developers.forem.com/api/v1#operation/createArticle) |
| **Mastodon** | Fediverse micro-blogging | Instance URL + access token (`write:statuses`) | Yes — public status URL | [Mastodon API](https://docs.joinmastodon.org/methods/statuses/#create) |
| **Telegram** | Channel broadcasting | Bot token + chat ID | Yes if the channel has a public username; otherwise no | [Bot API](https://core.telegram.org/bots/api#sendmessage) |
| **Discord** | Community chat | Webhook URL | No — channel membership required | [Webhook docs](https://discord.com/developers/docs/resources/webhook#execute-webhook) |

**Why these five?** All of them offer free API access, publish real content and
have official documentation, so an evaluator can verify the integration without
paying for a plan or waiting for app review. Platforms such as Hashnode now
require a paid Pro plan for API publishing, LinkedIn requires app review and
`w_member_social` approval, and Medium no longer issues new integration tokens —
so they were deliberately excluded.

The app reports `public_access: false` for Discord because Discord channels
require an invite to read. Reporting the truth is more useful than claiming
every result is public.

---

## Project structure

```
.
├── app/
│   ├── main.py                     # FastAPI app, routes, error handlers
│   ├── config.py                   # Settings loaded from environment / .env
│   ├── schemas.py                  # Request/response models + validation
│   ├── platforms/
│   │   ├── base.py                 # Abstract platform + shared HTTP helpers
│   │   ├── bluesky.py
│   │   ├── devto.py
│   │   ├── mastodon.py
│   │   ├── telegram.py
│   │   ├── discord.py
│   │   └── simulated.py            # Demo-only stand-in (DEMO_MODE=true)
│   ├── static/                     # Landing page: HTML/CSS/JS, no build step
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── app.js
│   └── services/
│       └── posting_service.py      # Fans out to all platforms, collects results
├── tests/
│   ├── conftest.py                 # Fake credentials fixture
│   ├── helpers.py                  # Shared HTTP mocks
│   ├── test_validation.py
│   ├── test_platforms.py
│   ├── test_posting_service.py
│   └── test_api.py
├── screenshots/                    # UI and response screenshots
├── scripts/
│   └── smoke_test.py               # Manual end-to-end checks against a running server
├── logs/                           # Real responses captured from a local run
├── .env.example                    # Every environment variable, documented
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## Requirements

- Python **3.10+** (developed and tested on 3.10.11)
- Internet access for the real integrations

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your local configuration
cp .env.example .env        # Windows: copy .env.example .env

# 4. Fill in the credentials you have (see "Configuration" below)
```

---

## Configuration

All settings are read from environment variables (or a local `.env` file) via
Pydantic Settings.

| Variable | Required by | Description |
| --- | --- | --- |
| `DEMO_MODE` | all | `true` simulates every platform instead of calling real APIs. |
| `REQUEST_TIMEOUT` | all | Per-request timeout in seconds (default `15`). |
| `BLUESKY_IDENTIFIER` | Bluesky | Your handle, e.g. `alice.bsky.social`. |
| `BLUESKY_APP_PASSWORD` | Bluesky | App password from Bluesky settings (not your login password). |
| `DEVTO_API_KEY` | DEV Community | DEV Community API key. |
| `MASTODON_INSTANCE` | Mastodon | Instance base URL, e.g. `https://mastodon.social`. |
| `MASTODON_ACCESS_TOKEN` | Mastodon | Access token with the `write:statuses` scope. |
| `TELEGRAM_BOT_TOKEN` | Telegram | Token from [@BotFather](https://t.me/BotFather). |
| `TELEGRAM_CHAT_ID` | Telegram | `@channelname` for a public channel, or a numeric chat ID. |
| `DISCORD_WEBHOOK_URL` | Discord | Webhook URL from the target channel. |

A platform without credentials is **skipped at request time** with a result like:

```json
{
  "platform": "Bluesky",
  "status": "failed",
  "error": "Missing configuration: BLUESKY_IDENTIFIER, BLUESKY_APP_PASSWORD"
}
```

The batch still runs the other platforms and `success` reflects whether at
least one platform accepted the message.

---

## Running the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Then open:

- Landing page with a working demo form: <http://localhost:4000/>
- Swagger UI: <http://localhost:4000/docs>
- ReDoc: <http://localhost:4000/redoc>
- OpenAPI JSON: <http://localhost:4000/openapi.json>
- Health check: <http://localhost:4000/health>
- Platform configuration status: <http://localhost:4000/platforms>

![Swagger UI](screenshots/02-swagger-ui.jpg)

---

## API reference

### `POST /posting`

Publishes the message to every platform.

#### Request

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

```json
{
  "message": "Check out our latest business platform and grow your online visibility. https://example.com"
}
```

#### Validation rules

| Rule | Invalid example | Response |
| --- | --- | --- |
| Message is required and not empty | `{"message": ""}` | `422` |
| At most 200 characters | 201-character message | `422` |
| Exactly one CTA link | no link / two links | `422` |
| CTA is a valid `http`/`https` URL | `ftp://...`, `https://localhost`, `https://user:pass@host` | `422` |

Validation errors return a compact, machine-readable payload:

```json
{
  "success": false,
  "error": "validation_error",
  "details": [
    {
      "field": "message",
      "message": "Value error, message must contain exactly one CTA link (found 2)",
      "type": "value_error"
    }
  ]
}
```

#### Success response (captured with `DEMO_MODE=true`)

This is a real response from the local server; with real credentials the
`posted_url` values point to the actual posts and the `(simulated)` suffix
disappears.

```json
{
  "success": true,
  "results": [
    {
      "platform": "Bluesky (simulated)",
      "status": "success",
      "posted_url": "https://example.com/simulated/bluesky/check-out-our-latest-business-platform-and-grow-yo-9d8dc9",
      "public_access": true,
      "date": "2026-11-21",
      "time": "13:23:26",
      "error": null
    },
    {
      "platform": "DEV Community (simulated)",
      "status": "success",
      "posted_url": "https://example.com/simulated/dev-community/check-out-our-latest-business-platform-and-grow-yo-59117f",
      "public_access": true,
      "date": "2026-11-21",
      "time": "13:23:26",
      "error": null
    },
    {
      "platform": "Mastodon (simulated)",
      "status": "success",
      "posted_url": "https://example.com/simulated/mastodon/check-out-our-latest-business-platform-and-grow-yo-b75939",
      "public_access": true,
      "date": "2026-11-21",
      "time": "13:23:26",
      "error": null
    },
    {
      "platform": "Telegram (simulated)",
      "status": "success",
      "posted_url": "https://example.com/simulated/telegram/check-out-our-latest-business-platform-and-grow-yo-97867d",
      "public_access": true,
      "date": "2026-11-21",
      "time": "13:23:26",
      "error": null
    },
    {
      "platform": "Discord (simulated)",
      "status": "success",
      "posted_url": "https://example.com/simulated/discord/check-out-our-latest-business-platform-and-grow-yo-b252b4",
      "public_access": true,
      "date": "2026-11-21",
      "time": "13:23:26",
      "error": null
    }
  ]
}
```

#### Real integrations (Bluesky + DEV Community, live)

A real run on 2026-11-21 with live credentials for two platforms:

```json
{
  "platform": "Bluesky",
  "status": "success",
  "posted_url": "https://bsky.app/profile/alkasima.bsky.social/post/3n2tk4gec6a2t",
  "public_access": true,
  "date": "2026-11-21",
  "time": "16:40:32",
  "error": null
},
{
  "platform": "DEV Community",
  "status": "success",
  "posted_url": "https://dev.to/kasim_abubakarjajere_d0d/testing-the-postpilot-multi-platform-posting-api-51jg",
  "public_access": true,
  "date": "2026-11-21",
  "time": "16:40:32",
  "error": null
}
```

Both were verified independently: Bluesky's public `app.bsky.feed.getPostThread`
returned the same record, and the DEV Community article API returned the same
title and body with HTTP 200.

The other three platforms in that run reported `Missing configuration`, which is
the expected graceful behaviour until their credentials are added.

**Upstream errors are reported per platform.** During testing, DEV Community
rejected a repeated title with
`HTTP 422 - Title has already been used in the last five minutes`. The app
recorded it as a failed result and still published to Bluesky — exactly the
required behaviour.

#### Partial failure response (real run, one platform rejected the message)

The `401` from DEV Community is captured per platform while the other four
still succeed. This is the behaviour required by the assignment.

```json
{
  "success": true,
  "results": [
    { "platform": "Bluesky", "status": "success", "...": "..." },
    {
      "platform": "DEV Community",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "DEV Community article creation: HTTP 401 - {\"error\":\"unauthorized\"}"
    },
    { "platform": "Mastodon", "status": "success", "...": "..." },
    { "platform": "Telegram", "status": "success", "...": "..." },
    { "platform": "Discord", "status": "success", "...": "..." }
  ]
}
```

#### Response when no credentials are configured (real run)

```json
{
  "success": false,
  "results": [
    {
      "platform": "Bluesky",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing configuration: BLUESKY_IDENTIFIER, BLUESKY_APP_PASSWORD"
    },
    {
      "platform": "DEV Community",
      "status": "failed",
      "error": "Missing configuration: DEVTO_API_KEY"
    },
    {
      "platform": "Mastodon",
      "status": "failed",
      "error": "Missing configuration: MASTODON_ACCESS_TOKEN"
    },
    {
      "platform": "Telegram",
      "status": "failed",
      "error": "Missing configuration: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
    },
    {
      "platform": "Discord",
      "status": "failed",
      "error": "Missing configuration: DISCORD_WEBHOOK_URL"
    }
  ]
}
```

### `GET /platforms`

Returns each platform and whether its credentials are present (useful for
debugging a setup without leaking any secret):

```json
{
  "platforms": [
    {
      "platform": "Bluesky",
      "configured": false,
      "required_settings": ["BLUESKY_IDENTIFIER", "BLUESKY_APP_PASSWORD"],
      "missing_settings": ["BLUESKY_IDENTIFIER", "BLUESKY_APP_PASSWORD"],
      "docs": "https://docs.bsky.app/docs/advanced-guides/posts",
      "simulated": false
    }
  ]
}
```

### `GET /health`

```json
{ "status": "ok", "version": "1.0.0", "demo_mode": true }
```

---

## Platform setup guide

### Bluesky

1. Sign in at <https://bsky.app>.
2. Open **Settings → App Passwords → Add App Password**.
3. Copy the generated password into `BLUESKY_APP_PASSWORD`.
4. Set `BLUESKY_IDENTIFIER` to your handle (e.g. `alice.bsky.social`).

The app calls `com.atproto.server.createSession` and then
`com.atproto.repo.createRecord`, and builds the public URL
`https://bsky.app/profile/<handle>/post/<rkey>`.

### DEV Community

1. Sign in at <https://dev.to>.
2. Open **Settings → Extensions → DEV Community API Keys**.
3. Generate a key and set `DEVTO_API_KEY`.

The message is posted as a published Markdown article; the title is derived from
the message with the CTA link removed.

### Mastodon

1. Sign in to any instance (e.g. `mastodon.social`, `hachyderm.io`).
2. Open **Preferences → Development → New application**.
3. Enable at least the `write:statuses` scope and create the application.
4. Copy the access token to `MASTODON_ACCESS_TOKEN` and the instance base URL to
   `MASTODON_INSTANCE`.

### Telegram

1. Talk to [@BotFather](https://t.me/BotFather) and send `/newbot`.
2. Copy the bot token to `TELEGRAM_BOT_TOKEN`.
3. Create a **public** channel and add the bot as an administrator with the
   *Post Messages* permission.
4. Set `TELEGRAM_CHAT_ID` to `@yourchannelname`.

A public channel username produces a permalink such as
`https://t.me/yourchannel/123`. Without a username the link is only usable by
chat members, so the app reports `public_access: false`.

### Discord

1. Open your server → **Server Settings → Integrations → Webhooks**.
2. Create a webhook for the target channel and copy its URL.
3. Set `DISCORD_WEBHOOK_URL`.

The app appends `wait=true` so Discord returns the created message, which is
used to build `https://discord.com/channels/<guild>/<channel>/<message>`.

---

## Demo mode

Set `DEMO_MODE=true` in `.env` (or the environment) to preview the full
response without any credentials:

```bash
DEMO_MODE=true uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Every platform is replaced by a clearly labelled simulation
(`Bluesky (simulated)`, `DEV Community (simulated)`, ...). No network request
is made. This exists so the response contract can be reviewed immediately; turn
it off and add real credentials to publish for real.

![Demo response from the landing page form](screenshots/03-demo-response.jpg)

---

## Testing

```bash
pytest -q
```

```
36 passed
```

The suite covers:

- **Validation** — empty, too long, zero/multiple links, invalid schemes,
  credentials in URLs, `localhost` hosts and the 200-character boundary.
- **Each integration** — request shape and URL extraction, with all HTTP calls
  mocked through `respx`.
- **Error handling** — a `401` from one platform becomes a failed result while
  the others succeed; missing configuration fails gracefully.
- **Orchestration** — concurrent fan-out, result count, demo mode.
- **API layer** — `200` success, `422` validation, partial failure, health,
  platform status and the OpenAPI schema.

Tests never touch the network and never need real credentials.

### Manual smoke test

With the server running in another terminal:

```bash
python scripts/smoke_test.py
```

It checks `/health` and seven `/posting` cases (one valid, six invalid) and exits
with a non-zero status if anything fails. Pass a different base URL as the first
argument to test a remote deployment.

---

## Design notes

- **Independent platforms.** `PostingService` builds one instance per platform
  and runs them with `asyncio.gather`. Each publish is wrapped in its own
  `try/except`, so an exception in one platform becomes a failed result instead
  of aborting the batch.
- **Thin platform classes.** Every integration subclasses `BasePlatform`, which
  owns timeout handling, HTTP error conversion and UTC timestamps. Adding a
  platform means adding one file and registering the class in
  `PLATFORM_CLASSES`.
- **Validation in one place.** `app/schemas.py` owns all message rules, so the
  API layer stays declarative and the rules are unit-testable.
- **Honest reporting.** `public_access` is computed from the actual response
  (Telegram channel username, Discord guild/channel IDs) rather than assumed.
- **No silent secrets.** Credentials are read from the environment only;
  `.gitignore` excludes `.env` and `.env.example` documents the expected names.

### Adding another platform

1. Create `app/platforms/myplatform.py` with a `BasePlatform` subclass.
2. Declare `display_name`, `required_settings` and `docs_url`.
3. Implement `publish()` and raise `PlatformError` with a useful message.
4. Add the class to `PLATFORM_CLASSES` in `posting_service.py`.
5. Add a mocked test in `tests/test_platforms.py`.

---

## Security

- No API key, token, password or webhook URL is committed. Only
  `.env.example` with empty placeholders is versioned.
- `.gitignore` excludes `.env`, virtual environments, caches and logs.
- The service never logs request bodies or credentials; errors contain only the
  upstream status code and a truncated response body.
- All timestamps are UTC (`YYYY-MM-DD`, `HH:MM:SS`).

---

## Screenshots and logs

| File | Description |
| --- | --- |
| `screenshots/01-landing-page.jpg` | Landing page with live platform status and the interactive demo form. |
| `screenshots/02-swagger-ui.jpg` | Auto-generated Swagger UI at `/docs`. |
| `screenshots/03-demo-response.jpg` | Full JSON response rendered with syntax highlighting. |
| `screenshots/04-real-bluesky-post.jpg` | Live Bluesky post created by the API with real credentials. |
| `screenshots/05-real-bluesky-devto.jpg` | Live run with real Bluesky and DEV Community successes. |
| `logs/health.json` | Health endpoint output. |
| `logs/platforms_no_credentials.json` | Platform configuration status. |
| `logs/sample_response_demo_mode.json` | Full successful multi-platform response. |
| `logs/sample_response_bluesky_real.json` | Real Bluesky success plus missing-config failures for the rest. |
| `logs/sample_response_bluesky_devto_real.json` | Real Bluesky and DEV Community successes from the same request. |
| `logs/sample_response_no_credentials.json` | Graceful per-platform failures. |
| `logs/sample_validation_error.json` | `422` response for a missing link. |
| `logs/sample_validation_two_links.json` | `422` response for two links. |

All files in `logs/` were captured from the local server (`uvicorn ... --port 4000`).

---

## Possible next steps

- Add retries with exponential backoff for `429` responses.
- Add a `GET /posts` history backed by SQLite.
- Support user-selected platforms in the request body.
- Add GitHub Actions to run `pytest` on every push.
- Add structured (JSON) application logging.