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


if __name__ == "__main__":
    unittest.main()
