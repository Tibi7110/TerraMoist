"""Smoke test: hit a running backend and save a demo tile to disk.

Usage:
1. In one terminal, start the backend from `web/backend`:
       uvicorn app.main:app --reload
2. From the repo root, run:
       python scripts/smoke_test.py
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

API = os.getenv("TERRAMOIST_API", "http://127.0.0.1:8000")
SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    try:
        # Confirm the app is up and the backend configuration loaded.
        r = httpx.get(f"{API}/api/v1/health", timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Backend is not reachable at {API}: {exc}", file=sys.stderr)
        return 1

    print("Health:", r.json())
    if not r.json()["cdse_configured"]:
        print("CDSE credentials missing in web/.env.example/.env setup.", file=sys.stderr)
        return 1

    # Pick the small demo window over Baragan.
    r = httpx.get(f"{API}/api/v1/regions", timeout=10)
    r.raise_for_status()
    regions = r.json()["regions"]
    baragan = next(x for x in regions if x["id"] == "baragan_small")
    print("Using region:", baragan["name"])

    # Request an NDMI tile for the last 30 days over the selected region.
    today = date.today()
    body = {
        "index": "ndmi",
        "bbox": baragan["bbox"],
        "date_from": (today - timedelta(days=30)).isoformat(),
        "date_to": today.isoformat(),
        "width": 512,
        "height": 512,
    }
    r = httpx.post(f"{API}/api/v1/tiles", json=body, timeout=120)
    if r.status_code != 200:
        print(
            "Tile request failed:",
            r.status_code,
            r.text[:500],
            file=sys.stderr,
        )
        return 1

    out = SCRIPT_DIR / "ndmi_baragan.png"
    out.write_bytes(r.content)
    print(f"Saved {out} ({len(r.content):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
