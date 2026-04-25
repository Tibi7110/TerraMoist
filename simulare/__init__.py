"""Standalone irrigation simulation package.

This package is intentionally isolated from the existing web app.
"""

from .engine import build_start_result
from .schemas import (
    IrrigationStartRequest,
    IrrigationStartResult,
    IrrigationRunStatus,
)
from .service import SimulationService

__all__ = [
    "build_start_result",
    "IrrigationStartRequest",
    "IrrigationStartResult",
    "IrrigationRunStatus",
    "SimulationService",
]
