import sqlite3
import tempfile
import unittest
from pathlib import Path

from astra_core.storage import LATEST_SCHEMA_VERSION, SQLiteStore


class StorageMigrationTests(unittest.TestCase):
    def test_fresh_database_reaches_latest_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "astra.db")
            self.assertEqual(
                store._conn.execute("PRAGMA user_version").fetchone()[0],
                LATEST_SCHEMA_VERSION,
            )
            self.assertIsNotNone(
                store._conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='goals'"
                ).fetchone()
            )
            self.assertIsNotNone(
                store._conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='intentions'"
                ).fetchone()
            )
            self.assertIsNotNone(
                store._conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='executive_ticks'"
                ).fetchone()
            )
            store.close()

    def test_legacy_remote_schema_migrates_without_data_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.db"
            conn = sqlite3.connect(path)
            conn.executescript("""
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    execution_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE TABLE execution_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    stage TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(execution_id, sequence)
                );
                CREATE TABLE memory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER,
                    store_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE world_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER,
                    version INTEGER NOT NULL,
                    snapshot TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE world_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER,
                    event TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)
            conn.execute(
                "INSERT INTO executions(identity, goal, status, verified, created_at) "
                "VALUES ('legacy', 'preserve me', 'completed', 1, "
                "'2026-01-01T00:00:00+00:00')"
            )
            conn.execute(
                "INSERT INTO memory_items(store_name, content, provenance, confidence, created_at) "
                "VALUES ('semantic', 'legacy memory', 'legacy-source', .7, "
                "'2026-01-01T00:00:00+00:00')"
            )
            conn.execute(
                "INSERT INTO tasks(goal, status, attempts, created_at, updated_at) "
                "VALUES ('legacy task', 'queued', 0, '2026-01-01T00:00:00+00:00', "
                "'2026-01-01T00:00:00+00:00')"
            )
            conn.commit()
            conn.close()

            store = SQLiteStore(path)
            self.assertEqual(
                store._conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0], 1
            )
            execution = store._conn.execute(
                "SELECT mode, state FROM executions WHERE identity = 'legacy'"
            ).fetchone()
            self.assertEqual(execution["mode"], "sandbox")
            self.assertEqual(execution["state"], "created")
            self.assertEqual(
                store._conn.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0], 1
            )
            self.assertEqual(
                store._conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 1
            )
            self.assertEqual(
                store._conn.execute("PRAGMA user_version").fetchone()[0],
                LATEST_SCHEMA_VERSION,
            )
            row = store._conn.execute(
                "SELECT category, knowledge_version, status, updated_at FROM memory_items"
            ).fetchone()
            self.assertEqual(row["category"], "general")
            self.assertEqual(row["knowledge_version"], "unknown")
            self.assertEqual(row["status"], "active")
            self.assertIsNotNone(row["updated_at"])
            task = store._conn.execute(
                "SELECT goal_id FROM tasks WHERE goal = 'legacy task'"
            ).fetchone()
            self.assertIsNotNone(task["goal_id"])
            self.assertEqual(
                store._conn.execute("SELECT COUNT(*) FROM executive_ticks").fetchone()[0],
                0,
            )
            store.close()

    def test_memory_lifecycle_excludes_invalidated_and_superseded_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "astra.db")
            old_id = store.add_memory(
                "semantic",
                "the old fact",
                "source-a",
                .8,
            )
            self.assertEqual(len(store.search_memory("old fact")), 1)
            new_id = store.add_memory(
                "semantic",
                "the revised fact",
                "source-b",
                .9,
                supersedes_id=old_id,
            )
            self.assertEqual(store.get_memory(old_id)["status"], "superseded")
            self.assertEqual(store.get_memory(new_id)["status"], "active")
            self.assertEqual(len(store.search_memory("old fact")), 0)
            self.assertEqual(len(store.search_memory("revised fact")), 1)
            store.update_memory_status(new_id, "invalidated")
            self.assertEqual(len(store.search_memory("revised fact")), 0)
            store.close()

    def test_prospective_intention_store_is_typed_and_triggerable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "astra.db")
            task_id = store.create_task("remember to verify")
            intention_id = store.create_intention(
                "Verify the saved artifact",
                "event",
                "artifact.ready",
                priority=9,
                task_id=task_id,
                payload={"artifact": "demo.txt"},
            )
            intention = store.get_intention(intention_id)
            self.assertEqual(intention["status"], "pending")
            self.assertEqual(intention["cue_type"], "event")
            due = store.list_due_intentions("event", "artifact.ready")
            self.assertEqual(len(due), 1)
            self.assertEqual(due[0]["id"], intention_id)
            self.assertEqual(store.get_intention(intention_id)["status"], "due")
            store.set_intention_status(intention_id, "completed")
            self.assertEqual(store.get_intention(intention_id)["status"], "completed")
            store.close()

    def test_time_intention_uses_due_at_without_context_injection(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "astra.db")
            intention_id = store.create_intention(
                "Perform the scheduled review",
                "time",
                "2026-09-20T10:00:00+00:00",
                due_at="2026-09-20T10:00:00+00:00",
            )
            due = store.list_due_intentions(
                "time",
                now="2026-09-20T10:01:00+00:00",
            )
            self.assertEqual([item["id"] for item in due], [intention_id])
            self.assertEqual(store.get_intention(intention_id)["status"], "due")
            store.close()

    def test_task_state_is_keyed_and_versioned(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "astra.db")
            task_id = store.create_task("persistent task", priority=7)
            goal_id = store.get_task(task_id)["goal_id"]
            self.assertEqual(store.get_goal(goal_id)["priority"], 7)
            self.assertEqual(
                store.set_task_state(task_id, "checkpoint", {"step": 1}), 1
            )
            self.assertEqual(
                store.set_task_state(task_id, "checkpoint", {"step": 2}), 2
            )
            state = store.get_task_state(task_id, "checkpoint")
            self.assertEqual(state["version"], 2)
            self.assertEqual(state["value"], {"step": 2})
            store.close()


if __name__ == "__main__":
    unittest.main()
