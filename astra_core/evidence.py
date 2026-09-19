"""Evidence objects keep generated output distinct from verified observations."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Evidence:
    source: str
    content: Any
    evidence_type: str
    confidence: float
    observed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class EvidenceLedger:
    def __init__(self):
        self._items: list[Evidence] = []

    def add(self, evidence: Evidence) -> Evidence:
        self._items.append(evidence)
        return evidence

    def all(self) -> list[Evidence]:
        return list(self._items)

    def verified(self) -> list[Evidence]:
        return [item for item in self._items if item.evidence_type == "verified"]
