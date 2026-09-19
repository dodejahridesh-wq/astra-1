"""Persistent execution runtime for Astra-1."""
from __future__ import annotations

from .collective import sign_packet
from .evidence import Evidence, EvidenceLedger
from .execution import ExecutionState, ExecutionStateMachine
from .governance import assess_action
from .memory import MemorySystem
from .modes import ExecutionMode
from .models import DeterministicProvider, ModelProvider
from .retrieval import SQLiteMemoryRetriever
from .router import ModelRouter
from .skills import Skill, SkillRegistry
from .storage import SQLiteStore
from .verification import verify
from .world import WorldModel


class PersistentRuntime:
    """Run the cognitive loop with durable execution state and explicit boundaries."""

    def __init__(
        self,
        store: SQLiteStore | None = None,
        provider: ModelProvider | None = None,
        identity: str = "astra-1-runtime",
    ):
        self.store = store or SQLiteStore()
        self.router = ModelRouter(provider or DeterministicProvider())
        self.identity = identity
        self.memory = MemorySystem()
        self.retriever = SQLiteMemoryRetriever(self.store)
        snapshot = self.store.get_latest_world_snapshot()
        self.world = WorldModel.from_snapshot(snapshot["snapshot"]) if snapshot else WorldModel()
        self.skills = SkillRegistry()

    def _emit(self, execution_id: int, sequence: int, stage: str, payload: object) -> dict:
        event = {"sequence": sequence, "stage": stage, "payload": payload}
        self.store.append_event(execution_id, sequence, stage, payload)
        return event

    def create_task(self, goal: str) -> int:
        return self.store.create_task(goal)

    def resume_task(self, task_id: int, mode: ExecutionMode | str = ExecutionMode.SANDBOX) -> dict:
        task = self.store.get_task(task_id)
        if task is None:
            raise ValueError("unknown task")
        if task["status"] == "completed":
            return {"task_id": task_id, "status": "completed", "execution_id": task["execution_id"]}
        result = self.run(task["goal"], mode, task_id=task_id)
        return {**result, "task_id": task_id, "resumed": True}

    def run(self, goal: str, mode: ExecutionMode | str = ExecutionMode.SANDBOX, task_id: int | None = None) -> dict:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal must be a non-empty string")
        mode = ExecutionMode(mode)
        machine = ExecutionStateMachine()
        execution_id = self.store.create_execution(self.identity, goal, mode.value, task_id=task_id)
        machine.transition(ExecutionState.RUNNING)

        events: list[dict] = []
        evidence = EvidenceLedger()

        try:
            events.append(self._emit(execution_id, 1, "Goal", goal))
            events.append(self._emit(
                execution_id, 2, "Perceive",
                {"mode": mode.value, "external_side_effects": mode.permits_external_side_effects},
            ))

            memories = self.retriever.retrieve(goal)
            events.append(self._emit(
                execution_id, 3, "Retrieve",
                [{"provenance": m.provenance, "confidence": m.confidence} for m in memories],
            ))

            model = self.router.generate(goal)
            events.append(self._emit(execution_id, 4, "Model", model.text))

            plan = self.router.generate(goal, "planner")
            events.append(self._emit(execution_id, 5, "Plan", plan.text))

            events.append(self._emit(
                execution_id, 6, "Simulate",
                {"mode": ExecutionMode.SIMULATION.value, "external_side_effects": False},
            ))

            is_external = mode is ExecutionMode.LIVE
            decision = assess_action("sandbox-demo", external=is_external)
            events.append(self._emit(
                execution_id, 7, "Act",
                {"allowed": decision.allowed, "reason": decision.reason, "mode": mode.value},
            ))

            if not decision.allowed:
                machine.transition(ExecutionState.BLOCKED)
                self.store.update_execution_state(execution_id, machine.state.value)
                self.store.finish_execution(execution_id, "blocked", False)
                if task_id is not None:
                    self.store.update_task(task_id, "blocked", execution_id)
                return {
                    "execution_id": execution_id,
                    "goal": goal,
                    "mode": mode.value,
                    "status": "blocked",
                    "verified": False,
                    "trace": events,
                }

            observed = {
                "goal": goal,
                "action": "sandbox-demo",
                "allowed": decision.allowed,
                "mode": mode.value,
            }
            self.world.observe(observed)
            self.store.add_world_event(observed, execution_id)
            evidence.add(Evidence("world-model", observed, "observed", .95))
            events.append(self._emit(execution_id, 8, "Observe", observed))

            machine.transition(ExecutionState.VERIFYING)
            self.store.update_execution_state(execution_id, machine.state.value)

            verification = verify(
                [{"stage": e["stage"], "payload": e["payload"]} for e in events],
                "sandbox-demo",
            )
            if verification.passed:
                evidence.add(Evidence(
                    "execution-trace", verification.notes, "verified", .90
                ))
            events.append(self._emit(execution_id, 9, "Verify", verification.notes))

            reflection = self.router.generate(goal, "reflector")
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

            machine.transition(ExecutionState.COMPLETED)
            self.store.finish_execution(execution_id, "completed", verification.passed)
            if task_id is not None:
                self.store.update_task(task_id, "completed", execution_id)
            return {
                "execution_id": execution_id,
                "goal": goal,
                "mode": mode.value,
                "status": "completed",
                "verified": verification.passed,
                "evidence": [e.__dict__ for e in evidence.all()],
                "trace": events,
            }
        except Exception:
            if machine.state not in {ExecutionState.COMPLETED, ExecutionState.BLOCKED}:
                if machine.state is ExecutionState.CREATED:
                    machine.transition(ExecutionState.RUNNING)
                if machine.state in {ExecutionState.RUNNING, ExecutionState.VERIFYING}:
                    machine.transition(ExecutionState.FAILED)
            self.store.finish_execution(execution_id, "failed", False)
            if task_id is not None:
                self.store.update_task(task_id, "failed", execution_id)
            raise
