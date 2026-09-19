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
        source_reliability: float = 1.0,
    ) -> int:
        source_reliability = float(source_reliability)
        if not 0.0 <= source_reliability <= 1.0:
            raise ValueError("source_reliability must be between 0 and 1")
        prediction_confidence = float(prediction_confidence)
        if not 0.0 <= prediction_confidence <= 1.0:
            raise ValueError("prediction_confidence must be between 0 and 1")
        error = {
            "action": action,
            "predicted": predicted,
            "observed": observed,
            "prediction_confidence": prediction_confidence,
            "source_reliability": source_reliability,
            "evidence_weight": prediction_confidence * source_reliability,
            "matched": predicted == observed,
            "provenance": provenance,
        }
        self.prediction_errors.append(error)
        if not error["matched"]:
            self._revise_from_prediction_error(error)
        self.version += 1
        return self.version

    def _revise_from_prediction_error(
        self,
        error: dict[str, Any],
        mismatch_threshold: int = 2,
        min_revision_confidence: float = 0.65,
        min_margin: float = 0.20,
    ) -> None:
        """Revise only when weighted evidence distinguishes competing outcomes.

        Prediction errors are immutable evidence. Evidence weight combines the
        confidence of the original prediction with the reliability assigned to
        its source. When competing observed outcomes remain too close, the
        world model explicitly abstains instead of selecting a hypothesis.
        """
        action = error["action"]
        predicted = error["predicted"]
        repeated = [
            item
            for item in self.prediction_errors
            if item["action"] == action
            and item["predicted"] == predicted
            and not item["matched"]
        ]
        if len(repeated) < mismatch_threshold:
            return

        weights: dict[str, float] = {}
        examples: dict[str, Any] = {}
        counts: dict[str, int] = {}
        for item in repeated:
            key = repr(item["observed"])
            weights[key] = weights.get(key, 0.0) + float(
                item.get("evidence_weight", item.get("prediction_confidence", 1.0))
            )
            examples[key] = item["observed"]
            counts[key] = counts.get(key, 0) + 1

        ranked = sorted(weights.items(), key=lambda pair: (-pair[1], pair[0]))
        total_weight = sum(weights.values())
        winner_key, winner_weight = ranked[0]
        second_weight = ranked[1][1] if len(ranked) > 1 else 0.0
        revision_confidence = winner_weight / total_weight if total_weight else 0.0
        margin = (
            (winner_weight - second_weight) / total_weight
            if total_weight
            else 0.0
        )
        winner = examples[winner_key]

        if (
            len(ranked) > 1
            and (
                revision_confidence < min_revision_confidence
                or margin < min_margin
            )
        ):
            self.model_revisions.append({
                "action": action,
                "superseded_outcome": predicted,
                "revised_outcome": None,
                "mismatch_count": len(repeated),
                "status": "abstained",
                "provenance": "prediction-error",
                "revision_confidence": revision_confidence,
                "evidence_weight": winner_weight,
                "competing_outcomes": [
                    {"outcome": examples[key], "evidence_weight": weight, "count": counts[key]}
                    for key, weight in ranked
                ],
                "reason": "competing evidence could not be distinguished",
            })
            return

        existing = None
        for hypothesis in reversed(self.hypotheses):
            if (
                hypothesis.get("kind") == "transition_rule"
                and hypothesis.get("action") == action
                and hypothesis.get("expected_outcome") == winner
                and hypothesis.get("status", "active") == "active"
            ):
                existing = hypothesis
                break
        if existing is not None:
            existing["evidence_count"] = counts[winner_key]
            existing["evidence_weight"] = winner_weight
            existing["confidence"] = revision_confidence
            for revision in reversed(self.model_revisions):
                if (
                    revision["action"] == action
                    and revision["superseded_outcome"] == predicted
                    and revision["revised_outcome"] == winner
                    and revision["status"] == "active"
                ):
                    revision["mismatch_count"] = len(repeated)
                    revision["revision_confidence"] = revision_confidence
                    revision["evidence_weight"] = winner_weight
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
            "revised_outcome": winner,
            "mismatch_count": len(repeated),
            "status": "active",
            "provenance": "prediction-error",
            "revision_confidence": revision_confidence,
            "evidence_weight": winner_weight,
            "competing_outcomes": [
                {"outcome": examples[key], "evidence_weight": weight, "count": counts[key]}
                for key, weight in ranked
            ],
        }
        self.hypotheses.append({
            "statement": f"{action} is better modeled as producing {winner!r} than {predicted!r}.",
            "kind": "transition_rule",
            "action": action,
            "expected_outcome": winner,
            "confidence": revision_confidence,
            "evidence_weight": winner_weight,
            "provenance": "prediction-error",
            "status": "active",
            "evidence_count": counts[winner_key],
        })
        self.model_revisions.append(revision)

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> "WorldModel":
        snapshot = dict(snapshot)
        snapshot.setdefault("model_revisions", [])
        return cls(**snapshot)
