"""Explicit execution state machine for persistent Astra tasks."""
from dataclasses import dataclass
from enum import Enum


class ExecutionState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


_TRANSITIONS = {
    ExecutionState.CREATED: {ExecutionState.RUNNING, ExecutionState.BLOCKED},
    ExecutionState.RUNNING: {ExecutionState.VERIFYING, ExecutionState.FAILED, ExecutionState.BLOCKED},
    ExecutionState.VERIFYING: {ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.BLOCKED},
    ExecutionState.COMPLETED: set(),
    ExecutionState.FAILED: set(),
    ExecutionState.BLOCKED: set(),
}


@dataclass
class ExecutionStateMachine:
    state: ExecutionState = ExecutionState.CREATED

    def transition(self, target: ExecutionState) -> ExecutionState:
        if target not in _TRANSITIONS[self.state]:
            raise ValueError(f"invalid execution transition: {self.state.value} -> {target.value}")
        self.state = target
        return self.state
