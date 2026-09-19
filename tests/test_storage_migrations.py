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
                    mode TEXT NOT NULL DEFAULT 'sandbox',
                    state TEXT NOT NULL DEFAULT 'created',
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
                "INSERT INTO executions(identity, goal, status, mode, state, verified, created_at) "
                "VALUES ('legacy', 'preserve me', 'completed', 'sandbox', 'completed', 1, "
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
                "SELECT category, knowledge_version FROM memory_items"
            ).fetchone()
            self.assertEqual(row["category"], "general")
            self.assertEqual(row["knowledge_version"], "unknown")
            task = store._conn.execute(
                "SELECT goal_id FROM tasks WHERE goal = 'legacy task'"
            ).fetchone()
            self.assertIsNotNone(task["goal_id"])
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
