"""ESP32 irrigation simulation routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from simulare.schemas import IrrigationRunStatus, IrrigationStartRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/simulare", tags=["simulation"])


class StopRunRequest(BaseModel):
    reason: str = Field(default="manual-stop", min_length=3, max_length=64)


@router.post("/start", response_model=IrrigationRunStatus)
async def start_simulation(
    body: IrrigationStartRequest,
    request: Request,
) -> IrrigationRunStatus:
    return request.app.state.simulation_service.start_run(body)


@router.get("", response_model=list[IrrigationRunStatus])
async def list_simulations(request: Request) -> list[IrrigationRunStatus]:
    return request.app.state.simulation_service.list_runs()


@router.get("/{run_id}", response_model=IrrigationRunStatus)
async def get_simulation(run_id: str, request: Request) -> IrrigationRunStatus:
    run = request.app.state.simulation_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return run


@router.post("/{run_id}/stop", response_model=IrrigationRunStatus)
async def stop_simulation(
    run_id: str,
    body: StopRunRequest,
    request: Request,
) -> IrrigationRunStatus:
    run = request.app.state.simulation_service.stop_run(run_id, reason=body.reason)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return run


@router.post("/{run_id}/complete", response_model=IrrigationRunStatus)
async def complete_simulation(run_id: str, request: Request) -> IrrigationRunStatus:
    run = request.app.state.simulation_service.complete_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return run
