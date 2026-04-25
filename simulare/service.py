"""In-memory simulation runtime service."""
from __future__ import annotations

from datetime import datetime, timezone

from .engine import build_start_result
from .schemas import IrrigationRunStatus, IrrigationStartRequest


class SimulationService:
    """Store and manage simulated irrigation runs in memory."""

    def __init__(self) -> None:
        self._runs: dict[str, IrrigationRunStatus] = {}

    def start_run(self, request: IrrigationStartRequest) -> IrrigationRunStatus:
        result = build_start_result(request)
        now = datetime.now(timezone.utc)
        status = IrrigationRunStatus(
            run_id=result.run_id,
            state="running",
            farmer_id=request.farmer_id,
            parcel_id=request.parcel_id,
            irrigation_system_type=request.irrigation_system_type,
            started_at=now,
            updated_at=now,
            result=result,
        )
        self._runs[result.run_id] = status
        return status

    def get_run(self, run_id: str) -> IrrigationRunStatus | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[IrrigationRunStatus]:
        return sorted(
            self._runs.values(),
            key=lambda run: run.updated_at,
            reverse=True,
        )

    def stop_run(self, run_id: str, reason: str = "manual-stop") -> IrrigationRunStatus | None:
        run = self._runs.get(run_id)
        if run is None:
            return None

        if run.state != "running":
            return run

        updated = run.model_copy(
            update={
                "state": "stopped",
                "updated_at": datetime.now(timezone.utc),
                "stopped_reason": reason,
            }
        )
        self._runs[run_id] = updated
        return updated

    def complete_run(self, run_id: str) -> IrrigationRunStatus | None:
        run = self._runs.get(run_id)
        if run is None:
            return None

        if run.state != "running":
            return run

        updated = run.model_copy(
            update={
                "state": "completed",
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._runs[run_id] = updated
        return updated
