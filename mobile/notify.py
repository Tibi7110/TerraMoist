"""TerraMoist daily irrigation notifier.

Runs the full irrigation pipeline (satellite tile → weather → FAO-56 model)
and sends a Web Push notification to all registered devices if irrigation
is recommended.

Usage (manual):
    cd /path/to/CASSINI_HACKATHON
    python mobile/notify.py

Usage (automated, every morning at 07:00):
    # Add to crontab with:  crontab -e
    0 7 * * * cd /path/to/CASSINI_HACKATHON && python mobile/notify.py >> mobile/notify.log 2>&1

Devices that subscribed to push (phone + paired smartwatch) will receive
the alert automatically via the Web Push API.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

API = "http://127.0.0.1:8000"
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from irrigation_model import IrrigationModel  # noqa: E402
from weather_agent import WeatherAgent        # noqa: E402


# Default region: Bărăgan small demo window.
DEMO_BBOX = (27.30, 44.55, 27.50, 44.70)


def run() -> int:
    # ── 1. Fetch NDMI tile from backend ──────────────────────────────────
    try:
        health = httpx.get(f"{API}/api/v1/health", timeout=10)
        health.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"[notify] Backend not reachable: {exc}", file=sys.stderr)
        return 1

    today = date.today()
    tile_resp = httpx.post(
        f"{API}/api/v1/tiles",
        json={
            "index": "ndmi",
            "bbox": list(DEMO_BBOX),
            "date_from": (today - timedelta(days=30)).isoformat(),
            "date_to": today.isoformat(),
            "width": 256,
            "height": 256,
        },
        timeout=120,
    )
    if tile_resp.status_code != 200:
        print(f"[notify] Tile request failed: {tile_resp.status_code}", file=sys.stderr)
        return 1

    # ── 2. Weather forecast ───────────────────────────────────────────────
    forecast = WeatherAgent().forecast_for_bbox(DEMO_BBOX)

    # ── 3. FAO-56 irrigation recommendation ──────────────────────────────
    recommendation = IrrigationModel().recommend(
        ndmi_png=tile_resp.content,
        weather=forecast,
    )

    print(f"[notify] should_irrigate={recommendation.should_irrigate} "
          f"deficit={recommendation.water_balance.final_deficit_mm:.1f}mm "
          f"recommended={recommendation.recommended_irrigation_mm:.1f}mm")

    if not recommendation.should_irrigate:
        print("[notify] No irrigation needed today — no push sent.")
        return 0

    # ── 4. Send push notification to all subscribed devices ──────────────
    mm = recommendation.recommended_irrigation_mm
    deficit = recommendation.water_balance.final_deficit_mm
    dry_pct = int(recommendation.moisture.dry_pixel_ratio * 100)

    push_resp = httpx.post(
        f"{API}/api/v1/push/send",
        json={
            "title": "💧 TerraMoist — Irrigate Today",
            "body": (
                f"Soil moisture deficit: {deficit:.0f}mm. "
                f"{dry_pct}% of your field is dry. "
                f"Recommended irrigation: {mm:.0f}mm."
            ),
            "url": "/",
        },
        timeout=30,
    )
    result = push_resp.json()
    print(f"[notify] Push sent to {result['sent']} device(s), {result['failed']} failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
