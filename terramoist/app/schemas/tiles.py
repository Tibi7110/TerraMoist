"""Pydantic models for request/response validation."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Three indices the backend knows how to render. Using Literal here gives us
# both FastAPI-generated OpenAPI enum values and runtime validation for free.
IndexName = Literal["ndmi", "sar_moisture", "true_color"]


class TileRequest(BaseModel):
    """Body of POST /api/v1/tiles."""

    index: IndexName = Field(description="Which index to render")
    bbox: tuple[float, float, float, float] = Field(
        description=(
            "Bounding box: (min_lon, min_lat, max_lon, max_lat) in EPSG:4326"
        ),
    )
    date_from: date = Field(description="Start of time window (YYYY-MM-DD)")
    date_to: date = Field(description="End of time window (YYYY-MM-DD)")
    width: int = Field(default=512, ge=64, le=2500)
    height: int = Field(default=512, ge=64, le=2500)

    @field_validator("bbox")
    @classmethod
    def _validate_bbox(
        cls, v: tuple[float, float, float, float]
    ) -> tuple[float, float, float, float]:
        """Catch common bbox mistakes before we hit Sentinel Hub.

        Sentinel Hub rejects malformed or oversized bounding boxes with
        unhelpful errors. We reject them locally with a clear message.
        """
        min_lon, min_lat, max_lon, max_lat = v
        if not (-180 <= min_lon < max_lon <= 180):
            raise ValueError("Longitude range invalid")
        if not (-90 <= min_lat < max_lat <= 90):
            raise ValueError("Latitude range invalid")
        # 5-degree cap keeps the request under Sentinel Hub's per-request
        # processing budget for a 512x512 tile.
        if (max_lon - min_lon) > 5 or (max_lat - min_lat) > 5:
            raise ValueError("Bounding box too large (max 5 degrees per side)")
        return v


class HealthResponse(BaseModel):
    """Response model for GET /api/v1/health."""

    status: Literal["ok"]
    cdse_configured: bool