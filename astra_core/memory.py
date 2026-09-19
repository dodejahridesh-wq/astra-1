from dataclasses import dataclass, field
from typing import Any

@dataclass
class MemoryItem:
    content: Any
    provenance: str
    confidence: float
    tags: list[str] = field(default_factory=list)
    category: str = "general"
    knowledge_version: str = "unknown"

class MemorySystem:
    STORES = ("working", "episodic", "semantic", "procedural", "autobiographical")

    def __init__(self):
        for store in self.STORES:
            setattr(self, store, [])

    def add(
        self, store, content, provenance="sandbox", confidence=.8, tags=None,
        category="general", knowledge_version="unknown"
    ):
        if store not in self.STORES:
            raise ValueError(f"unknown memory store: {store}")
        item = MemoryItem(
            content, provenance, confidence, tags or [], category, knowledge_version
        )
        getattr(self, store).append(item)
        return item

    def retrieve(self, query):
        q = query.lower()
        return [
            m for store in self.STORES
            for m in getattr(self, store)
            if q in str(m.content).lower()
        ]
