"""Schemas for backend-only irrigation simulation."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

IrrigationSystemType = Literal["fixed", "mobile"]
RunState = Literal["running", "stopped", "completed"]


class IrrigationStartRequest(BaseModel):
    """Input needed to start an irrigation run simulation."""

    farmer_id: str = Field(min_length=1, max_length=120)
    parcel_id: str = Field(min_length=1, max_length=120)
    parcel_name: str = Field(min_length=1, max_length=120)
    bbox: tuple[float, float, float, float]
    area_hectares: float = Field(gt=0, le=10000)
    recommended_irrigation_mm: float = Field(gt=0, le=120)
    irrigation_system_type: IrrigationSystemType
    subscription_plan: str = Field(default="basic", min_length=3, max_length=32)


class IrrigationCommandPayload(BaseModel):
    """Simulated command message sent to ESP32 over MQTT-like transport."""

    action: Literal["start_irrigation"]
    farm_id: str
    parcel_id: str
    parcel_name: str
    irrigation_system_type: IrrigationSystemType
    target_mm: float
    water_volume_liters: float
    estimated_duration_minutes: int
    zone_count: int
    bbox: list[float]


class IrrigationStartResult(BaseModel):
    """Result returned after starting a simulated irrigation run."""

    run_id: str
    status: Literal["accepted"]
    message: str
    topic: str
    water_volume_liters: float
    estimated_duration_minutes: int
    estimated_water_saved_liters: float
    command_payload: IrrigationCommandPayload
    farmer_notification: str


class IrrigationRunStatus(BaseModel):
    """Runtime status for one simulated irrigation run."""

    run_id: str
    state: RunState
    farmer_id: str
    parcel_id: str
    irrigation_system_type: IrrigationSystemType
    started_at: datetime
    updated_at: datetime
    stopped_reason: str | None = None
    result: IrrigationStartResult
