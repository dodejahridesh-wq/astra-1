"""Typed prospective-memory primitives for Astra-1."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntentionStatus(str, Enum):
    PENDING = "pending"
    ARMED = "armed"
    DUE = "due"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class CueType(str, Enum):
    TIME = "time"
    EVENT = "event"
    STATE = "state"
    MANUAL = "manual"


@dataclass(frozen=True)
class ProspectiveIntention:
    id: int
    description: str
    cue_type: CueType
    cue_value: str
    priority: int
    status: IntentionStatus
    due_at: str | None
    goal_id: int | None
    task_id: int | None
    execution_id: int | None
    provenance: str
    payload: dict
    created_at: str
    updated_at: str
    triggered_at: str | None = None
