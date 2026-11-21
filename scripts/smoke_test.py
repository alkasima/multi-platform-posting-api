#!/usr/bin/env python3
"""Manual smoke test for a running PostPilot server.

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py http://localhost:4000

Checks the health endpoint and seven ``/posting`` cases (one valid, six invalid).
Exits with status 1 if any check fails.
"""

from __future__ import annotations

import sys

import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:4000"
TIMEOUT = 30.0

CASES = [
    (
        "valid message",
        {
            "message": "Check out our latest business platform and grow your "
            "online visibility. https://example.com"
        },
        200,
    ),
    ("no link", {"message": "This message has no link at all."}, 422),
    (
        "two links",
        {"message": "First https://example.com then https://example.org"},
        422,
    ),
    ("too long", {"message": "a" * 201 + " https://example.com"}, 422),
    ("empty message", {"message": ""}, 422),
    ("non-http scheme", {"message": "Try ftp://example.com/file"}, 422),
    ("localhost host", {"message": "Try https://localhost/page"}, 422),
]


def main() -> int:
    failures = 0
    print(f"PostPilot smoke test against {BASE_URL}\n")

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        try:
            health = client.get("/health")
            ok = health.status_code == 200
            failures += not ok
            print(
                f"[{'PASS' if ok else 'FAIL'}] GET /health -> "
                f"{health.status_code} {health.text}"
            )
        except httpx.HTTPError as exc:
            print(f"[FAIL] GET /health -> {exc}")
            return 1

        for name, payload, expected in CASES:
            try:
                response = client.post("/posting", json=payload)
                ok = response.status_code == expected
                failures += not ok
                print(
                    f"[{'PASS' if ok else 'FAIL'}] {name}: "
                    f"expected {expected}, got {response.status_code}"
                )
                if name == "valid message" and ok:
                    body = response.json()
                    results = body.get("results", [])
                    succeeded = sum(
                        1 for item in results if item.get("status") == "success"
                    )
                    print(
                        f"       success={body.get('success')} "
                        f"platforms={len(results)} succeeded={succeeded}"
                    )
                    for item in results:
                        detail = item.get("posted_url") or item.get("error")
                        print(f"       - {item['platform']}: {item['status']} {detail}")
                elif not ok:
                    print(f"       {response.text[:300]}")
            except httpx.HTTPError as exc:
                failures += 1
                print(f"[FAIL] {name}: {exc}")

    print()
    if failures:
        print(f"{failures} check(s) failed")
        return 1
    print("All checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())