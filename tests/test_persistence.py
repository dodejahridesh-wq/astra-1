import tempfile
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from threading import Thread
from http.server import ThreadingHTTPServer

from astra_core.runtime import PersistentRuntime
from astra_core.service import AstraRequestHandler
from astra_core.storage import SQLiteStore


class PersistenceTests(unittest.TestCase):
    def test_execution_survives_runtime_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "astra.db"
            store = SQLiteStore(db)
            result = PersistentRuntime(store=store).run("remember this execution")
            execution_id = result["execution_id"]
            store.close()

            reopened = SQLiteStore(db)
            saved = reopened.get_execution(execution_id)
            self.assertIsNotNone(saved)
            self.assertEqual(saved["status"], "completed")
            self.assertEqual(saved["state"], "completed")
            self.assertEqual(saved["mode"], "sandbox")
            self.assertTrue(saved["verified"])
            self.assertEqual(len(saved["events"]), 14)
            self.assertEqual([e["sequence"] for e in saved["events"]], list(range(1, 15)))
            self.assertEqual(len(reopened.get_world_events()), 1)
            snapshot = reopened.get_latest_world_snapshot()
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot["version"], 1)
            self.assertEqual(len(snapshot["snapshot"]["events"]), 1)
            reopened.close()

    def test_live_mode_is_blocked_without_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "astra.db")
            result = PersistentRuntime(store=store).run("attempt external action", "live")
            self.assertEqual(result["status"], "blocked")
            saved = store.get_execution(result["execution_id"])
            self.assertEqual(saved["state"], "blocked")
            self.assertFalse(saved["verified"])
            store.close()

    def test_health_and_run_http_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            AstraRequestHandler.runtime = PersistentRuntime(
                store=SQLiteStore(Path(tmp) / "astra.db")
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), AstraRequestHandler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_address[1]}"
                with urlopen(f"{base}/health") as response:
                    self.assertEqual(response.status, 200)
                request = Request(
                    f"{base}/run",
                    data=b'{"goal":"validate persistent api"}',
                    headers={"Content-Type":"application/json"},
                    method="POST",
                )
                with urlopen(request) as response:
                    payload = response.read().decode()
                    self.assertEqual(response.status, 200)
                    self.assertIn('"execution_id"', payload)
            finally:
                server.shutdown()
                server.server_close()
                AstraRequestHandler.runtime.store.close()

    def test_runtime_exposes_prospective_intention_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "astra.db")
            runtime = PersistentRuntime(store=store)
            intention_id = runtime.create_intention(
                "Review the benchmark output",
                "event",
                "benchmark.complete",
                priority=5,
                provenance="test",
            )
            self.assertEqual(
                runtime.poll_intentions("event", "benchmark.complete")[0]["id"],
                intention_id,
            )
            runtime.complete_intention(intention_id)
            store.close()

    def test_temporal_executive_dispatches_due_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "astra.db")
            runtime = PersistentRuntime(store=store)
            intention_id = runtime.create_intention(
                "verify the deferred artifact",
                "event",
                "artifact.ready",
                priority=10,
            )
            tick = runtime.tick(
                now="2026-09-20T10:00:00+00:00",
                event_cues=("artifact.ready",),
            )
            self.assertEqual(tick.due_intentions, (intention_id,))
            self.assertEqual(tick.dispatched_intentions, (intention_id,))
            self.assertEqual(tick.completed_intentions, (intention_id,))
            self.assertEqual(store.get_intention(intention_id)["status"], "completed")
            self.assertEqual(len(store.get_executive_ticks()), 1)
            store.close()

    def test_temporal_executive_can_wake_without_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "astra.db")
            runtime = PersistentRuntime(store=store)
            intention_id = runtime.create_intention(
                "scheduled review",
                "time",
                "2026-09-20T10:00:00+00:00",
                due_at="2026-09-20T10:00:00+00:00",
            )
            tick = runtime.tick(
                now="2026-09-20T10:01:00+00:00",
                dispatch=False,
            )
            self.assertEqual(tick.due_intentions, (intention_id,))
            self.assertEqual(tick.dispatched_intentions, ())
            self.assertEqual(store.get_intention(intention_id)["status"], "due")
            store.close()

    def test_predictive_world_state_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "astra.db"
            store = SQLiteStore(db)
            runtime = PersistentRuntime(store=store)
            runtime.record_transition("lookup", {"result": "found"})
            runtime.record_transition("lookup", {"result": "found"})
            runtime.record_transition("lookup", {"result": "missing"})
            prediction = runtime.predict("lookup", min_confidence=0.6)
            self.assertIsNotNone(prediction)
            self.assertEqual(prediction.predicted_outcome, {"result": "found"})
            store.close()

            reopened = SQLiteStore(db)
            restored = PersistentRuntime(store=reopened)
            prediction = restored.predict("lookup", min_confidence=0.6)
            self.assertIsNotNone(prediction)
            self.assertEqual(prediction.predicted_outcome, {"result": "found"})
            restored.record_prediction_error(
                "lookup",
                {"result": "found"},
                {"result": "missing"},
                prediction_confidence=2 / 3,
            )
            snapshot = reopened.get_latest_world_snapshot()
            self.assertEqual(len(snapshot["snapshot"]["prediction_errors"]), 1)
            reopened.close()

    def test_task_can_be_resumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "astra.db")
            runtime = PersistentRuntime(store=store)
            task_id = runtime.create_task("resume this task")
            result = runtime.resume_task(task_id)
            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["resumed"])
            task = store.get_task(task_id)
            self.assertEqual(task["status"], "completed")
            self.assertEqual(task["attempts"], 1)
            store.close()


if __name__ == "__main__":
    unittest.main()
