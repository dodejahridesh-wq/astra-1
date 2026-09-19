"""Execution modes used to keep simulation separate from live actions."""
from enum import Enum


class ExecutionMode(str, Enum):
    SANDBOX = "sandbox"
    SIMULATION = "simulation"
    LIVE = "live"

    @property
    def permits_external_side_effects(self) -> bool:
        return self is ExecutionMode.LIVE
