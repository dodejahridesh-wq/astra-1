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
            self.assertEqual(len(saved["events"]), 13)
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
