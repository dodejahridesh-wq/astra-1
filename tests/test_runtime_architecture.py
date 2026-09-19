import tempfile
import unittest
from pathlib import Path

from astra_core.evidence import Evidence, EvidenceLedger
from astra_core.execution import ExecutionState, ExecutionStateMachine
from astra_core.modes import ExecutionMode
from astra_core.retrieval import MemoryRetriever
from astra_core.memory import MemorySystem
from astra_core.models import DeterministicProvider
from astra_core.router import ModelRouter
from astra_core.scheduling import CognitiveScheduler
from astra_core.world import WorldModel
from astra_core.foresight import SelectiveForesight


class RuntimeArchitectureTests(unittest.TestCase):
    def test_execution_state_machine(self):
        machine = ExecutionStateMachine()
        machine.transition(ExecutionState.RUNNING)
        machine.transition(ExecutionState.VERIFYING)
        machine.transition(ExecutionState.COMPLETED)
        self.assertEqual(machine.state, ExecutionState.COMPLETED)
        with self.assertRaises(ValueError):
            machine.transition(ExecutionState.RUNNING)

    def test_modes_never_treat_sandbox_as_live(self):
        self.assertFalse(ExecutionMode.SANDBOX.permits_external_side_effects)
        self.assertFalse(ExecutionMode.SIMULATION.permits_external_side_effects)
        self.assertTrue(ExecutionMode.LIVE.permits_external_side_effects)

    def test_retrieval_and_evidence_are_explicit(self):
        memory = MemorySystem()
        memory.add("semantic", "persistent cognitive runtime", "test-source", .9)
        results = MemoryRetriever(memory).retrieve("persistent")
        self.assertEqual(results[0].provenance, "test-source")

        ledger = EvidenceLedger()
        ledger.add(Evidence("test", "observed", "verified", .95))
        self.assertEqual(len(ledger.verified()), 1)

    def test_router_preserves_provider_boundary(self):
        router = ModelRouter(DeterministicProvider())
        response = router.generate("test", "planner")
        self.assertEqual(response.provenance, "sandbox-model")

    def test_selective_foresight_requires_repeated_grounded_transitions(self):
        world = WorldModel()
        world.record_transition("open_file", {"status": "ok"})
        world.record_transition("open_file", {"status": "ok"})
        world.record_transition("open_file", {"status": "error"})
        prediction = SelectiveForesight(world).predict("open_file", min_confidence=0.6)
        self.assertIsNotNone(prediction)
        self.assertEqual(prediction.predicted_outcome, {"status": "ok"})
        self.assertAlmostEqual(prediction.confidence, 2 / 3)

        uncertain = SelectiveForesight(world).predict("delete_file", min_confidence=0.0)
        self.assertIsNone(uncertain)

    def test_repeated_prediction_errors_revise_hypothesis_without_erasing_history(self):
        world = WorldModel()
        predicted = {"status": "ok"}
        observed = {"status": "error"}
        world.add_hypothesis(
            "open_file is expected to produce ok.",
            confidence=0.9,
            provenance="inference",
        )
        world.hypotheses[-1].update(
            {
                "kind": "transition_rule",
                "action": "open_file",
                "expected_outcome": predicted,
                "status": "active",
            }
        )
        world.record_prediction_error(
            "open_file",
            predicted,
            observed,
            prediction_confidence=0.9,
        )
        self.assertEqual(len(world.model_revisions), 0)
        world.record_prediction_error(
            "open_file",
            predicted,
            observed,
            prediction_confidence=0.9,
        )

        self.assertEqual(len(world.prediction_errors), 2)
        self.assertEqual(len(world.model_revisions), 1)
        self.assertEqual(world.model_revisions[0]["mismatch_count"], 2)
        self.assertEqual(world.hypotheses[0]["status"], "revised")
        revised = world.hypotheses[-1]
        self.assertEqual(revised["expected_outcome"], observed)
        self.assertEqual(revised["status"], "active")

        world.record_prediction_error(
            "open_file",
            predicted,
            observed,
            prediction_confidence=0.9,
        )
        self.assertEqual(len(world.prediction_errors), 3)
        self.assertEqual(len(world.model_revisions), 1)
        self.assertEqual(world.hypotheses[-1]["evidence_count"], 3)

    def test_scheduler_allocates_bounded_profiles(self):
        scheduler = CognitiveScheduler()
        fast = scheduler.schedule("check status")
        deep = scheduler.schedule("research and analyze this complex design and verify the evidence carefully")
        self.assertEqual(fast.profile, "fast")
        self.assertEqual(deep.profile, "deep")
        self.assertLessEqual(fast.budget.max_model_calls, 5)
        self.assertGreater(deep.budget.retrieval_limit, fast.budget.retrieval_limit)


if __name__ == "__main__":
    unittest.main()
