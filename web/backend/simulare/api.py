"""Standalone FastAPI for irrigation simulation backend."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .schemas import IrrigationRunStatus, IrrigationStartRequest
from .service import SimulationService

app = FastAPI(
    title="TerraMoist Simulation API",
    version="0.1.0",
    description="Backend-only ESP32 irrigation simulation endpoints.",
)
_service = SimulationService()


class StopRunRequest(BaseModel):
    reason: str = Field(default="manual-stop", min_length=3, max_length=64)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "simulare"}


@app.post("/simulare/start", response_model=IrrigationRunStatus)
async def start_simulation(request: IrrigationStartRequest) -> IrrigationRunStatus:
    return _service.start_run(request)


@app.get("/simulare", response_model=list[IrrigationRunStatus])
async def list_simulations() -> list[IrrigationRunStatus]:
    return _service.list_runs()


@app.get("/simulare/{run_id}", response_model=IrrigationRunStatus)
async def get_simulation(run_id: str) -> IrrigationRunStatus:
    run = _service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return run


@app.post("/simulare/{run_id}/stop", response_model=IrrigationRunStatus)
async def stop_simulation(run_id: str, body: StopRunRequest) -> IrrigationRunStatus:
    run = _service.stop_run(run_id, reason=body.reason)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return run


@app.post("/simulare/{run_id}/complete", response_model=IrrigationRunStatus)
async def complete_simulation(run_id: str) -> IrrigationRunStatus:
    run = _service.complete_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return run
