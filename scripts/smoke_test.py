"""Smoke test: hit a running backend and run the irrigation agent pipeline.

Usage:
1. In one terminal, start the backend from `web/backend`:
       uvicorn app.main:app --reload
2. From the repo root, run:
       python scripts/smoke_test.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

from irrigation_model import IrrigationModel
from weather_agent import WeatherAgent

API = os.getenv("TERRAMOIST_API", "http://127.0.0.1:8000")
SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run NDMI + weather + irrigation recommendation for a region."
    )
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Custom bbox in EPSG:4326. Example: --bbox 27.35 44.60 27.37 44.615",
    )
    parser.add_argument(
        "--parcel-json",
        type=Path,
        help=(
            "Path to a frontend parcel JSON file. Accepts one parcel object or "
            "an array of parcels with points as [[lat,lng], ...]."
        ),
    )
    parser.add_argument(
        "--parcel-id",
        help="Parcel id to select when --parcel-json contains an array.",
    )
    parser.add_argument(
        "--region-id",
        default="baragan_small",
        help="Backend preset region id used when no custom bbox/parcel is passed.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=10,
        help="Lookback window for Sentinel imagery. Lower is more current; default: 10.",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=512,
        help="Output tile width/height in pixels. Default: 512.",
    )
    return parser.parse_args()


def bbox_from_parcel_file(path: Path, parcel_id: str | None) -> tuple[str, tuple[float, float, float, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        if parcel_id:
            parcel = next((item for item in payload if item.get("id") == parcel_id), None)
            if parcel is None:
                raise ValueError(f"Parcel id not found in {path}: {parcel_id}")
        else:
            if not payload:
                raise ValueError(f"Parcel file is empty: {path}")
            parcel = payload[0]
    elif isinstance(payload, dict):
        parcel = payload
    else:
        raise ValueError("Parcel JSON must be an object or an array")

    points = parcel.get("points")
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError("Parcel JSON must contain at least 3 points")

    lats = [float(point[0]) for point in points]
    lngs = [float(point[1]) for point in points]
    bbox = (min(lngs), min(lats), max(lngs), max(lats))
    return parcel.get("name", parcel.get("id", "custom parcel")), bbox


def select_region(args: argparse.Namespace) -> tuple[str, tuple[float, float, float, float]]:
    if args.bbox:
        return "Custom bbox", tuple(args.bbox)

    if args.parcel_json:
        return bbox_from_parcel_file(args.parcel_json, args.parcel_id)

    r = httpx.get(f"{API}/api/v1/regions", timeout=10)
    r.raise_for_status()
    regions = r.json()["regions"]
    region = next(x for x in regions if x["id"] == args.region_id)
    return region["name"], tuple(region["bbox"])


def main() -> int:
    args = parse_args()

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

    try:
        region_name, bbox = select_region(args)
    except (httpx.HTTPError, StopIteration, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Could not load requested region: {exc}", file=sys.stderr)
        return 1

    print("Using region:", region_name)
    print("Using bbox:", bbox)

    # Request a recent NDMI tile over the selected region.
    today = date.today()
    body = {
        "index": "ndmi",
        "bbox": bbox,
        "date_from": (today - timedelta(days=args.days)).isoformat(),
        "date_to": today.isoformat(),
        "width": args.size,
        "height": args.size,
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

    out = SCRIPT_DIR / "ndmi_custom.png"
    out.write_bytes(r.content)
    print(f"Saved {out} ({len(r.content):,} bytes)")

    # Agent 2: weather forecast for the centre of the same bbox.
    try:
        forecast = WeatherAgent().forecast_for_bbox(bbox)
    except httpx.HTTPError as exc:
        print(f"Weather API request failed: {exc}", file=sys.stderr)
        return 1

    print("Weather:", forecast.to_dict())

    # Agent 3: baseline ML-style irrigation recommendation.
    recommendation = IrrigationModel().recommend(
        ndmi_png=r.content,
        weather=forecast,
    )
    recommendation_out = SCRIPT_DIR / "irrigation_recommendation.json"
    recommendation_out.write_text(
        json.dumps(recommendation.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    print("Recommendation:", recommendation.to_dict())
    print(f"Saved {recommendation_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
