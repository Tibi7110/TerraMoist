"""Schemas for irrigation recommendation requests and responses."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class IrrigationEvent(BaseModel):
    amountMm: float = Field(ge=0, le=200)
    appliedAt: str


class IrrigationRecommendationRequest(BaseModel):
    fieldId: str
    fieldName: str = "Selected parcel"
    points: list[tuple[float, float]] = Field(
        description="Parcel polygon points as [lat, lon] pairs."
    )
    plantType: str = "wheat"
    irrigationType: Literal["fixed", "moving"] = "fixed"
    irrigationEvents: list[IrrigationEvent] = Field(default_factory=list)
    lookbackDays: int = Field(default=10, ge=1, le=45)

    @field_validator("points")
    @classmethod
    def _validate_points(
        cls,
        value: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        if len(value) < 3:
            raise ValueError("At least 3 polygon points are required")
        for lat, lon in value:
            if not (-90 <= lat <= 90):
                raise ValueError("Latitude out of range")
            if not (-180 <= lon <= 180):
                raise ValueError("Longitude out of range")
        return value


class MoistureFeaturesResponse(BaseModel):
    valid_pixel_ratio: float
    moisture_score: float
    dry_pixel_ratio: float
    initial_water_deficit_mm: float


class WeatherDayResponse(BaseModel):
    date: str
    precipitation_mm: float
    et0_fao_mm: float
    max_temp_c: float


class WeatherFeaturesResponse(BaseModel):
    latitude: float
    longitude: float
    forecast_days: int
    daily: list[WeatherDayResponse]
    precipitation_next_7d_mm: float
    evapotranspiration_next_7d_mm: float
    water_balance_next_7d_mm: float


class WaterBalanceDayResponse(BaseModel):
    date: str
    previous_deficit_mm: float
    et0_mm: float
    precipitation_mm: float
    irrigation_mm: float
    deficit_mm: float


class WaterBalanceResponse(BaseModel):
    formula: str
    initial_deficit_mm: float
    final_deficit_mm: float
    irrigation_threshold_mm: float
    max_deficit_mm: float
    daily: list[WaterBalanceDayResponse]


class IrrigationScenarioResponse(BaseModel):
    category: Literal["ideal", "optimal", "enough"]
    label: str
    water_mm: float
    effective_water_mm: float
    water_saved_mm: float
    water_saved_percent: float
    projected_yield_percent: float


class IrrigationRecommendationResponse(BaseModel):
    should_irrigate: bool
    urgency: Literal["low", "medium", "high"]
    necessity_score: float
    recommended_irrigation_mm: float
    model_type: str
    confidence: float
    fallback_used: bool
    training_samples: int
    reason: str
    bbox: tuple[float, float, float, float]
    plant_type: str
    irrigation_type: Literal["fixed", "moving"]
    moisture: MoistureFeaturesResponse
    weather: WeatherFeaturesResponse
    water_balance: WaterBalanceResponse
    scenarios: list[IrrigationScenarioResponse]
