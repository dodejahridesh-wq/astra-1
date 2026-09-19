"""Explicit versioned world model for Astra-1."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class WorldModel:
    entities: dict[str, dict[str, Any]] = field(default_factory=dict)
    relations: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    version: int = 0

    def observe(self, event: Any, provenance: str = "runtime", confidence: float = 1.0) -> int:
        self.events.append({"event": event, "provenance": provenance, "confidence": confidence})
        self.version += 1
        return self.version

    def upsert_entity(self, entity_id: str, attributes: dict[str, Any], provenance: str = "runtime") -> int:
        self.entities[entity_id] = {"attributes": dict(attributes), "provenance": provenance}
        self.version += 1
        return self.version

    def add_relation(self, subject: str, predicate: str, object_: str, provenance: str = "runtime", confidence: float = 1.0) -> int:
        self.relations.append({"subject": subject, "predicate": predicate, "object": object_, "provenance": provenance, "confidence": confidence})
        self.version += 1
        return self.version

    def add_hypothesis(self, statement: str, confidence: float = 0.5, provenance: str = "inference") -> int:
        self.hypotheses.append({"statement": statement, "confidence": confidence, "provenance": provenance})
        self.version += 1
        return self.version

    def add_assumption(self, statement: str, provenance: str = "runtime") -> int:
        self.assumptions.append({"statement": statement, "provenance": provenance})
        self.version += 1
        return self.version

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> "WorldModel":
        return cls(**snapshot)
