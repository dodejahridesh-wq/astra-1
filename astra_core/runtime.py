"""Persistent execution runtime for Astra-1.

This module is the bridge from the original in-memory prototype to a durable
cognitive runtime. It deliberately uses the existing deterministic organism
components rather than hiding cognition inside the persistence layer.
"""
from __future__ import annotations

from .collective import sign_packet
from .governance import assess_action
from .memory import MemorySystem
from .models import DeterministicProvider, ModelProvider
from .skills import Skill, SkillRegistry
from .storage import SQLiteStore
from .verification import verify
from .world import WorldModel


class PersistentRuntime:
    """Run the Astra cognitive loop while persisting execution state."""

    def __init__(
        self,
        store: SQLiteStore | None = None,
        provider: ModelProvider | None = None,
        identity: str = "astra-1-runtime",
    ):
        self.store = store or SQLiteStore()
        self.provider = provider or DeterministicProvider()
        self.identity = identity
        self.memory = MemorySystem()
        self.world = WorldModel()
        self.skills = SkillRegistry()

    def _emit(self, execution_id: int, sequence: int, stage: str, payload: object) -> dict:
        event = {"sequence": sequence, "stage": stage, "payload": payload}
        self.store.append_event(execution_id, sequence, stage, payload)
        return event

    def run(self, goal: str) -> dict:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal must be a non-empty string")

        execution_id = self.store.create_execution(self.identity, goal)
        events: list[dict] = []

        try:
            events.append(self._emit(execution_id, 1, "Goal", goal))
            events.append(self._emit(
                execution_id, 2, "Perceive",
                "Received goal and initialized persistent runtime state.",
            ))

            memories = self.memory.retrieve(goal)
            events.append(self._emit(
                execution_id, 3, "Retrieve", f"{len(memories)} relevant in-process memories"
            ))

            model = self.provider.generate(goal)
            events.append(self._emit(execution_id, 4, "Model", model.text))

            plan = self.provider.generate(goal, "planner")
            events.append(self._emit(execution_id, 5, "Plan", plan.text))

            events.append(self._emit(
                execution_id, 6, "Simulate",
                {"mode": "simulation", "external_side_effects": False},
            ))

            decision = assess_action("sandbox-demo")
            events.append(self._emit(
                execution_id, 7, "Act",
                {"allowed": decision.allowed, "reason": decision.reason},
            ))

            observed = {
                "goal": goal,
                "action": "sandbox-demo",
                "allowed": decision.allowed,
            }
            self.world.observe(observed)
            events.append(self._emit(execution_id, 8, "Observe", observed))

            verification = verify(
                [{"stage": e["stage"], "payload": e["payload"]} for e in events],
                "sandbox-demo",
            )
            events.append(self._emit(execution_id, 9, "Verify", verification.notes))

            reflection = self.provider.generate(goal, "reflector")
            events.append(self._emit(execution_id, 10, "Reflect", reflection.text))

            trace_payload = [dict(event) for event in events]
            self.memory.add(
                "episodic", {"goal": goal, "trace": trace_payload},
                "execution-trace", .95
            )
            self.store.add_memory(
                "episodic", {"goal": goal, "trace": trace_payload},
                "execution-trace", .95, execution_id
            )
            events.append(self._emit(
                execution_id, 11, "Consolidate",
                "Execution trace persisted to episodic memory.",
            ))

            skill = Skill("sandbox-demo", "Validated low-risk sandbox execution workflow.")
            self.skills.register_candidate(skill)
            self.skills.evaluate(skill.name, .9)
            events.append(self._emit(
                execution_id, 12, "Learn",
                "Candidate skill evaluated and promoted.",
            ))

            packet = sign_packet(
                self.identity, "Sandbox execution completed", "execution-trace", .95
            )
            events.append(self._emit(
                execution_id, 13, "Collective",
                {"signature": packet.signature, "provenance": packet.provenance},
            ))

            self.store.finish_execution(execution_id, "completed", verification.passed)
            return {
                "execution_id": execution_id,
                "goal": goal,
                "status": "completed",
                "verified": verification.passed,
                "trace": events,
            }
        except Exception:
            self.store.finish_execution(execution_id, "failed", False)
            raise
