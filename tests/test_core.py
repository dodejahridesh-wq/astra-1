import unittest
from astra_core.organism import AstraOrganism
from astra_core.governance import assess_action
from astra_core.collective import sign_packet

class AstraCoreTests(unittest.TestCase):
    def test_end_to_end_loop(self):
        result=AstraOrganism().run("validate the sandbox")
        self.assertTrue(result["verified"])
        stages=[e["stage"] for e in result["trace"]]
        self.assertEqual(stages[:12], list(AstraOrganism.LOOP))
    def test_high_risk_requires_human(self):
        decision=assess_action("external irreversible action", irreversible=True, external=True)
        self.assertFalse(decision.allowed); self.assertTrue(decision.requires_human)
    def test_capability_metadata_is_preserved(self):
        decision=assess_action(
            "read local evidence",
            capability="filesystem.read",
            read_only=True,
            idempotent=True,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.capability, "filesystem.read")
        self.assertTrue(decision.read_only)
        self.assertTrue(decision.idempotent)

    def test_destructive_external_action_is_blocked(self):
        decision=assess_action(
            "delete remote data",
            capability="database.delete",
            destructive=True,
            external=True,
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_human)
        self.assertEqual(decision.risk, "high")

    def test_collective_packet_signature(self):
        self.assertEqual(len(sign_packet("a","claim","test",.9).signature),64)

if __name__ == "__main__": unittest.main()
