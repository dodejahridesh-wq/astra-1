import tempfile
import unittest
from pathlib import Path

from astra_core.runtime import PersistentRuntime
from astra_core.world import WorldModel
from astra_core.storage import SQLiteStore


class WorldModelRevisionTests(unittest.TestCase):
    def test_equal_conflicting_evidence_abstains(self):
        world = WorldModel()
        for observed in ("missing", "blocked"):
            world.record_prediction_error(
                "lookup",
                "found",
                observed,
                prediction_confidence=1.0,
                source_reliability=1.0,
            )

        self.assertEqual(len(world.model_revisions), 1)
        revision = world.model_revisions[0]
        self.assertEqual(revision["status"], "abstained")
        self.assertIsNone(revision["revised_outcome"])
        self.assertEqual(revision["revision_confidence"], 0.5)
        self.assertEqual(len(world.hypotheses), 0)
        self.assertEqual(len(world.prediction_errors), 2)

    def test_source_reliability_can_distinguish_competing_evidence(self):
        world = WorldModel()
        world.record_prediction_error(
            "lookup",
            "found",
            "missing",
            prediction_confidence=1.0,
            source_reliability=0.9,
        )
        world.record_prediction_error(
            "lookup",
            "found",
            "blocked",
            prediction_confidence=1.0,
            source_reliability=0.2,
        )

        revision = world.model_revisions[0]
        self.assertEqual(revision["status"], "active")
        self.assertEqual(revision["revised_outcome"], "missing")
        self.assertAlmostEqual(revision["revision_confidence"], 0.9 / 1.1)
        self.assertEqual(world.hypotheses[-1]["expected_outcome"], "missing")
        self.assertEqual(len(world.prediction_errors), 2)

    def test_legacy_prediction_errors_remain_revision_compatible(self):
        world = WorldModel()
        world.prediction_errors.append({
            "action": "lookup",
            "predicted": "found",
            "observed": "missing",
            "prediction_confidence": 1.0,
            "matched": False,
            "provenance": "legacy-test",
        })
        world.prediction_errors.append({
            "action": "lookup",
            "predicted": "found",
            "observed": "missing",
            "prediction_confidence": 1.0,
            "matched": False,
            "provenance": "legacy-test",
        })
        world._revise_from_prediction_error(world.prediction_errors[-1])

        self.assertEqual(world.model_revisions[0]["status"], "active")
        self.assertEqual(world.hypotheses[-1]["expected_outcome"], "missing")

    def test_weighted_revision_and_abstention_survive_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "astra.db"
            store = SQLiteStore(db)
            runtime = PersistentRuntime(store=store)
            runtime.record_prediction_error(
                "lookup",
                "found",
                "missing",
                prediction_confidence=1.0,
                source_reliability=0.9,
                provenance="trusted-observer",
            )
            runtime.record_prediction_error(
                "lookup",
                "found",
                "blocked",
                prediction_confidence=1.0,
                source_reliability=0.2,
                provenance="weak-observer",
            )
            store.close()

            reopened = SQLiteStore(db)
            restored = PersistentRuntime(store=reopened)
            snapshot = reopened.get_latest_world_snapshot()["snapshot"]
            revision = snapshot["model_revisions"][0]
            self.assertEqual(revision["status"], "active")
            self.assertAlmostEqual(revision["revision_confidence"], 0.9 / 1.1)
            self.assertEqual(revision["competing_outcomes"][0]["outcome"], "missing")
            self.assertEqual(restored.world.hypotheses[-1]["expected_outcome"], "missing")
            self.assertEqual(snapshot["prediction_errors"][0]["source_reliability"], 0.9)
            self.assertEqual(snapshot["prediction_errors"][1]["source_reliability"], 0.2)
            reopened.close()


if __name__ == "__main__":
    unittest.main()
