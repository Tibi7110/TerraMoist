"""Public API routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response

from app.schemas.tiles import HealthResponse, TileRequest
from app.services.regions import PRESETS

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
            # Encourage the browser to cache identical requests during a demo.
            "Cache-Control": "public, max-age=300",
        },
    )