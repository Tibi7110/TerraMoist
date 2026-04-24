"""Smoke test: hit a running backend and save a demo tile to disk.

Usage (in another terminal, after `uvicorn app.main:app --reload` is up):
    python scripts/smoke_test.py
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

API = "http://127.0.0.1:8000"


def main() -> int:
    # 1) Health check — confirms the app is up AND .env is loaded correctly.
    r = httpx.get(f"{API}/api/v1/health", timeout=10)
    r.raise_for_status()
    print("Health:", r.json())
    if not r.json()["cdse_configured"]:
        print("CDSE credentials missing in .env - aborting.", file=sys.stderr)
        return 1

    # 2) Regions — pick the small demo window over Bărăgan.
    r = httpx.get(f"{API}/api/v1/regions", timeout=10)
    r.raise_for_status()
    regions = r.json()["regions"]
    baragan = next(x for x in regions if x["id"] == "baragan_small")
    print("Using region:", baragan["name"])

    # 3) Request an NDMI tile for the last 30 days over the selected region.
    today = date.today()
    body = {
        "index": "ndmi",
        "bbox": baragan["bbox"],
        "date_from": (today - timedelta(days=30)).isoformat(),
        "date_to":   today.isoformat(),
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

    out = Path("ndmi_baragan.png")
    out.write_bytes(r.content)
    print(f"Saved {out} ({len(r.content):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())