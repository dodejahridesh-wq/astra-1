"""Deterministic cognitive resource scheduling for Astra-1."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceBudget:
    max_model_calls: int = 4
    retrieval_limit: int = 10
    max_cost_units: int = 10


@dataclass(frozen=True)
class ScheduleDecision:
    profile: str
    budget: ResourceBudget
    roles: tuple[str, ...]


class CognitiveScheduler:
    """Choose a bounded cognitive profile without hiding allocation decisions."""

    def schedule(self, goal: str) -> ScheduleDecision:
        words = len(goal.split())
        complexity = words + sum(
            goal.lower().count(token)
            for token in ("compare", "analyze", "design", "research", "verify")
        )
        if complexity >= 14:
            return ScheduleDecision(
                "deep",
                ResourceBudget(max_model_calls=5, retrieval_limit=20, max_cost_units=20),
                ("general", "planner", "verifier", "reflector"),
            )
        if complexity >= 7:
            return ScheduleDecision(
                "standard",
                ResourceBudget(max_model_calls=4, retrieval_limit=10, max_cost_units=12),
                ("general", "planner", "reflector"),
            )
        return ScheduleDecision(
            "fast",
            ResourceBudget(max_model_calls=3, retrieval_limit=5, max_cost_units=6),
            ("general", "planner"),
        )
