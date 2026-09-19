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
    transitions: list[dict[str, Any]] = field(default_factory=list)
    prediction_errors: list[dict[str, Any]] = field(default_factory=list)
    model_revisions: list[dict[str, Any]] = field(default_factory=list)
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

    def record_transition(
        self,
        action: str,
        outcome: Any,
        provenance: str = "observation",
        confidence: float = 1.0,
    ) -> int:
        self.transitions.append({
            "action": action,
            "outcome": outcome,
            "provenance": provenance,
            "confidence": float(confidence),
        })
        self.version += 1
        return self.version

    def transition_history(self, action: str) -> list[dict[str, Any]]:
        return [item for item in self.transitions if item["action"] == action]

    def record_prediction_error(
        self,
        action: str,
        predicted: Any,
        observed: Any,
        *,
        prediction_confidence: float,
        provenance: str = "runtime",
    ) -> int:
        error = {
            "action": action,
            "predicted": predicted,
            "observed": observed,
            "prediction_confidence": float(prediction_confidence),
            "matched": predicted == observed,
            "provenance": provenance,
        }
        self.prediction_errors.append(error)
        if not error["matched"]:
            self._revise_from_prediction_error(error)
        self.version += 1
        return self.version

    def _revise_from_prediction_error(self, error: dict[str, Any], mismatch_threshold: int = 2) -> None:
        """Revise an empirical hypothesis after repeated, consistent mismatches.

        Observations and prediction errors remain immutable history. A revision adds
        a new hypothesis and marks the superseded hypothesis as revised; it never
        rewrites the evidence that caused the revision.
        """
        action = error["action"]
        predicted = error["predicted"]
        observed = error["observed"]
        repeated = [
            item
            for item in self.prediction_errors
            if item["action"] == action
            and item["predicted"] == predicted
            and item["observed"] == observed
            and not item["matched"]
        ]
        if len(repeated) < mismatch_threshold:
            return

        existing = None
        for hypothesis in reversed(self.hypotheses):
            if (
                hypothesis.get("kind") == "transition_rule"
                and hypothesis.get("action") == action
                and hypothesis.get("expected_outcome") == observed
                and hypothesis.get("status", "active") == "active"
            ):
                existing = hypothesis
                break
        if existing is not None:
            existing["evidence_count"] = len(repeated)
            existing["confidence"] = min(1.0, len(repeated) / (len(repeated) + 1))
            for revision in reversed(self.model_revisions):
                if (
                    revision["action"] == action
                    and revision["superseded_outcome"] == predicted
                    and revision["revised_outcome"] == observed
                ):
                    revision["mismatch_count"] = len(repeated)
                    break
            return

        active = None
        for hypothesis in reversed(self.hypotheses):
            if (
                hypothesis.get("kind") == "transition_rule"
                and hypothesis.get("action") == action
                and hypothesis.get("expected_outcome") == predicted
                and hypothesis.get("status", "active") == "active"
            ):
                active = hypothesis
                break

        if active is not None:
            active["status"] = "revised"
            active["revised_by_mismatch_count"] = len(repeated)

        revision = {
            "action": action,
            "superseded_outcome": predicted,
            "revised_outcome": observed,
            "mismatch_count": len(repeated),
            "status": "active",
            "provenance": "prediction-error",
        }
        self.hypotheses.append({
            "statement": f"{action} is better modeled as producing {observed!r} than {predicted!r}.",
            "kind": "transition_rule",
            "action": action,
            "expected_outcome": observed,
            "confidence": min(1.0, len(repeated) / (len(repeated) + 1)),
            "provenance": "prediction-error",
            "status": "active",
            "evidence_count": len(repeated),
        })
        self.model_revisions.append(revision)

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> "WorldModel":
        snapshot = dict(snapshot)
        snapshot.setdefault("model_revisions", [])
        return cls(**snapshot)
