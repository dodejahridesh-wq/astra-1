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
    def test_collective_packet_signature(self):
        self.assertEqual(len(sign_packet("a","claim","test",.9).signature),64)

if __name__ == "__main__": unittest.main()
