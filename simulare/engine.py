"""Core simulation logic (pure functions)."""
from __future__ import annotations

from math import ceil
from uuid import uuid4

from .schemas import IrrigationCommandPayload, IrrigationStartRequest, IrrigationStartResult

_FLOW_LPM_BY_SYSTEM = {
    "fixed": 220,
    "mobile": 480,
}

_BASELINE_OVERWATER_FACTOR_BY_PLAN = {
    "basic": 1.35,
    "pro": 1.25,
    "enterprise": 1.15,
}


def _round1(value: float) -> float:
    return round(value, 1)


def build_start_result(request: IrrigationStartRequest) -> IrrigationStartResult:
    """Build deterministic simulation output for a start command."""
    run_id = f"run-{uuid4().hex[:12]}"

    water_volume_liters = (
        request.recommended_irrigation_mm * request.area_hectares * 10000
    )

    flow_lpm = _FLOW_LPM_BY_SYSTEM[request.irrigation_system_type]
    if request.irrigation_system_type == "fixed":
        zone_count = max(1, ceil(request.area_hectares / 2))
    else:
        zone_count = 1

    duration_minutes = max(1, ceil(water_volume_liters / flow_lpm))

    baseline_factor = _BASELINE_OVERWATER_FACTOR_BY_PLAN.get(
        request.subscription_plan.lower(),
        _BASELINE_OVERWATER_FACTOR_BY_PLAN["basic"],
    )
    baseline_mm = request.recommended_irrigation_mm * baseline_factor
    estimated_saved_liters = (
        (baseline_mm - request.recommended_irrigation_mm)
        * request.area_hectares
        * 10000
    )

    command = IrrigationCommandPayload(
        action="start_irrigation",
        farm_id=request.farmer_id,
        parcel_id=request.parcel_id,
        parcel_name=request.parcel_name,
        irrigation_system_type=request.irrigation_system_type,
        target_mm=round(request.recommended_irrigation_mm, 2),
        water_volume_liters=_round1(water_volume_liters),
        estimated_duration_minutes=duration_minutes,
        zone_count=zone_count,
        bbox=list(request.bbox),
    )

    topic = f"terramoist/farm/{request.farmer_id}/esp32/cmd"
    notification = (
        f"Start irrigation for {request.parcel_name}: "
        f"{command.target_mm} mm, ~{duration_minutes} min."
    )

    return IrrigationStartResult(
        run_id=run_id,
        status="accepted",
        message="ESP32 simulation accepted. Irrigation run started.",
        topic=topic,
        water_volume_liters=command.water_volume_liters,
        estimated_duration_minutes=duration_minutes,
        estimated_water_saved_liters=_round1(max(0.0, estimated_saved_liters)),
        command_payload=command,
        farmer_notification=notification,
    )
