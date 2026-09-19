"""Pluggable retrieval interfaces for Astra-1."""
from dataclasses import dataclass
from typing import Any, Protocol

@dataclass(frozen=True)
class RetrievalResult:
    content: Any
    provenance: str
    confidence: float
    category: str = "general"
    knowledge_version: str = "unknown"

class Retriever(Protocol):
    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]: ...

class MemoryRetriever:
    def __init__(self, memory):
        self.memory = memory

    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]:
        return [
            RetrievalResult(
                item.content, item.provenance, item.confidence,
                getattr(item, "category", "general"),
                getattr(item, "knowledge_version", "unknown"),
            )
            for item in self.memory.retrieve(query)[:limit]
        ]

class SQLiteMemoryRetriever:
    def __init__(self, store):
        self.store = store

    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]:
        return [
            RetrievalResult(
                row["content"], row["provenance"], row["confidence"],
                row.get("category", "general"),
                row.get("knowledge_version", "unknown"),
            )
            for row in self.store.search_memory(query, limit)
        ]
