"""Public API routes."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pywebpush import webpush, WebPushException

from app.schemas.tiles import HealthResponse, PushSubscription, PushSendRequest, TileRequest
from app.services.regions import PRESETS

# In-memory store for push subscriptions (persisted to disk for restarts).
_SUBS_FILE = Path(__file__).resolve().parent.parent.parent / "push_subscriptions.json"
_subscriptions: list[dict] = json.loads(_SUBS_FILE.read_text()) if _SUBS_FILE.exists() else []

VAPID_PRIVATE_KEY = (
    "-----BEGIN EC PRIVATE KEY-----\n"
    "MHcCAQEEICkr2zuNSCHCVg2Bb+iu1jnwrXH2xP9QoeY73AD8iPrtoAoGCCqGSM49\n"
    "AwEHoUQDQgAEIpMv9sw9AJjY0ZKUk20+p/aSZJ3ji7VZpOzbXzjW9aeGHoBVEFpN\n"
    "ZRf2XC9Ii05blU+X7/Y9ceFDwBnWE/yKIA==\n"
    "-----END EC PRIVATE KEY-----\n"
)
VAPID_CLAIMS = {"sub": "mailto:team@terramoist.app"}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Liveness probe + config sanity check.

    Returned from the frontend to decide whether to render the map or show
    a 'backend not configured' banner.
    """
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        cdse_configured=bool(
            settings.cdse_client_id and settings.cdse_client_secret
        ),
    )


@router.get("/regions")
async def list_regions() -> dict:
    """Return named preset regions (for the frontend dropdown)."""
    return {
        "regions": [
            {"id": rid, **meta} for rid, meta in PRESETS.items()
        ]
    }


@router.post(
    "/tiles",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
)
async def get_tile(req: TileRequest, request: Request) -> Response:
    """Return a PNG tile for the requested index / bbox / time window."""
    settings = request.app.state.settings
    if not settings.cdse_client_id or not settings.cdse_client_secret:
        raise HTTPException(
            status_code=503,
            detail=(
                "CDSE credentials not configured. "
                "Add CDSE_CLIENT_ID and CDSE_CLIENT_SECRET to web/backend/.env "
                "(see .env.example)."
            ),
        )

    sh_client = request.app.state.sentinel_hub
    try:
        png_bytes = await sh_client.fetch_tile_png(
            index=req.index,
            bbox=req.bbox,
            date_from=req.date_from.isoformat(),
            date_to=req.date_to.isoformat(),
            width=req.width,
            height=req.height,
        )
    except Exception as exc:
        logger.exception("Tile fetch failed")
        raise HTTPException(
            status_code=502,
            detail=f"Sentinel Hub error: {exc}",
        ) from exc

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=300",
        },
    )


# ── Push notification endpoints ───────────────────────────────────────────

@router.post("/push/subscribe", status_code=201)
async def push_subscribe(sub: PushSubscription) -> dict:
    """Register a browser push subscription."""
    sub_dict = sub.model_dump()
    if sub_dict not in _subscriptions:
        _subscriptions.append(sub_dict)
        _SUBS_FILE.write_text(json.dumps(_subscriptions, indent=2))
    return {"status": "subscribed", "total": len(_subscriptions)}


@router.post("/push/send")
async def push_send(req: PushSendRequest) -> dict:
    """Send a push notification to all subscribers (called by notify.py)."""
    payload = json.dumps({"title": req.title, "body": req.body, "url": req.url})
    sent, failed = 0, 0
    dead: list[dict] = []
    for sub in list(_subscriptions):
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
            )
            sent += 1
        except WebPushException as exc:
            logger.warning("Push failed for %s: %s", sub.get("endpoint", "?")[:60], exc)
            if exc.response and exc.response.status_code in (404, 410):
                dead.append(sub)
            failed += 1
    # Remove expired subscriptions
    for d in dead:
        _subscriptions.remove(d)
    if dead:
        _SUBS_FILE.write_text(json.dumps(_subscriptions, indent=2))
    return {"sent": sent, "failed": failed}