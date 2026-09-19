"""Pluggable retrieval interfaces for Astra-1."""
from dataclasses import dataclass
from typing import Protocol, Any


@dataclass(frozen=True)
class RetrievalResult:
    content: Any
    provenance: str
    confidence: float


class Retriever(Protocol):
    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]: ...


class MemoryRetriever:
    """Adapter over the existing MemorySystem."""

    def __init__(self, memory):
        self.memory = memory

    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]:
        items = self.memory.retrieve(query)
        return [
            RetrievalResult(item.content, item.provenance, item.confidence)
            for item in items[:limit]
        ]
