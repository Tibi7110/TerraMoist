"""Irrigation recommendation routes."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Request

from app.schemas.irrigation import (
    IrrigationRecommendationRequest,
    IrrigationRecommendationResponse,
)
from app.services.irrigation import bbox_from_points
from app.services.weather import WeatherClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/irrigation", tags=["irrigation"])


@router.post("/recommend", response_model=IrrigationRecommendationResponse)
async def recommend_irrigation(
    req: IrrigationRecommendationRequest,
    request: Request,
) -> dict:
    """Return an irrigation recommendation for a frontend parcel.

    The endpoint fetches fresh NDMI and weather, appends the current sample to
    local history, retrains the lightweight KNN model, and returns a suggestion.
    """
    settings = request.app.state.settings
    if not settings.cdse_client_id or not settings.cdse_client_secret:
        raise HTTPException(
            status_code=503,
            detail="CDSE credentials not configured.",
        )

    bbox = bbox_from_points(req.points)
    today = date.today()
    date_from = (today - timedelta(days=req.lookbackDays)).isoformat()
    date_to = today.isoformat()

    try:
        png_bytes = await request.app.state.sentinel_hub.fetch_tile_png(
            index="ndmi",
            bbox=bbox,
            date_from=date_from,
            date_to=date_to,
            width=512,
            height=512,
        )
        weather = await WeatherClient(
            request.app.state.http_client
        ).forecast_for_bbox(bbox)
        return request.app.state.irrigation_engine.recommend(
            field_id=req.fieldId,
            field_name=req.fieldName,
            plant_type=req.plantType,
            bbox=bbox,
            ndmi_png=png_bytes,
            weather=weather,
            irrigation_events=[
                event.model_dump() for event in req.irrigationEvents
            ],
        )
    except Exception as exc:
        logger.exception("Irrigation recommendation failed")
        raise HTTPException(
            status_code=502,
            detail=f"Irrigation recommendation failed: {exc}",
        ) from exc
