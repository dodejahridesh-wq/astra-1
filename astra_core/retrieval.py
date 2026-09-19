"""Pluggable retrieval interfaces for Astra-1."""
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RetrievalResult:
    content: Any
    provenance: str
    confidence: float


class Retriever(Protocol):
    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]: ...


class MemoryRetriever:
    """Adapter over the existing in-process MemorySystem."""

    def __init__(self, memory):
        self.memory = memory

    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]:
        items = self.memory.retrieve(query)
        return [
            RetrievalResult(item.content, item.provenance, item.confidence)
            for item in items[:limit]
        ]


class SQLiteMemoryRetriever:
    """Durable lexical retrieval over persisted memory records.

    V0.2 intentionally uses simple substring matching. The interface allows
    vector, hybrid, or external retrieval implementations later.
    """

    def __init__(self, store):
        self.store = store

    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]:
        return [
            RetrievalResult(row["content"], row["provenance"], row["confidence"])
            for row in self.store.search_memory(query, limit)
        ]
