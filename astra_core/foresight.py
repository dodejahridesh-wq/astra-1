"""Predictive world-model primitives and selective foresight."""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from typing import Any


@dataclass(frozen=True)
class Prediction:
    action: str
    predicted_outcome: Any
    confidence: float
    evidence_count: int
    world_version: int


class SelectiveForesight:
    """Generate only empirically grounded predictions above a confidence threshold."""

    def __init__(self, world_model):
        self.world = world_model

    def predict(self, action: str, min_confidence: float = 0.6) -> Prediction | None:
        transitions = self.world.transition_history(action)
        if not transitions:
            return None
        counts = Counter(repr(item["outcome"]) for item in transitions)
        key, count = counts.most_common(1)[0]
        confidence = count / len(transitions)
        if confidence < min_confidence:
            return None
        outcome = next(item["outcome"] for item in transitions if repr(item["outcome"]) == key)
        return Prediction(
            action=action,
            predicted_outcome=outcome,
            confidence=confidence,
            evidence_count=len(transitions),
            world_version=self.world.version,
        )

    def predict_many(
        self,
        actions: list[str],
        min_confidence: float = 0.6,
    ) -> list[Prediction]:
        predictions = []
        for action in actions:
            prediction = self.predict(action, min_confidence)
            if prediction is not None:
                predictions.append(prediction)
        return predictions
