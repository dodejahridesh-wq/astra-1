"""Durable SQLite storage for Astra-1 execution state and provenance."""
from __future__ import annotations
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LATEST_SCHEMA_VERSION = 3

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class SQLiteStore:
    """Transactional SQLite store with explicit, monotonic schema migrations."""

    def __init__(self, path: str | Path = "data/astra.db"):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        with self._lock, self._conn:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._create_baseline_schema()
            version = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
            if version == 0:
                self._conn.execute("PRAGMA user_version = 1")
                version = 1
            while version < LATEST_SCHEMA_VERSION:
                if version == 1:
                    self._migrate_v1_to_v2()
                elif version == 2:
                    self._migrate_v2_to_v3()
                else:
                    raise RuntimeError(f"unsupported Astra-1 schema version: {version}")
                version += 1
                self._conn.execute(f"PRAGMA user_version = {version}")

    def _create_baseline_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                attempts INTEGER NOT NULL DEFAULT 0,
                execution_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS executions (
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
            CREATE TABLE IF NOT EXISTS execution_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER NOT NULL,
                sequence INTEGER NOT NULL,
                stage TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(execution_id) REFERENCES executions(id) ON DELETE CASCADE,
                UNIQUE(execution_id, sequence)
            );
            CREATE TABLE IF NOT EXISTS memory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER,
                store_name TEXT NOT NULL,
                content TEXT NOT NULL,
                provenance TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(execution_id) REFERENCES executions(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS world_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER,
                version INTEGER NOT NULL,
                snapshot TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(execution_id) REFERENCES executions(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS world_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER,
                event TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(execution_id) REFERENCES executions(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_execution
                ON execution_events(execution_id, sequence);
            CREATE INDEX IF NOT EXISTS idx_memory_store
                ON memory_items(store_name, created_at);
            CREATE INDEX IF NOT EXISTS idx_world_events_created
                ON world_events(created_at);
        """)

    def _columns(self, table: str) -> set[str]:
        return {row["name"] for row in self._conn.execute(f"PRAGMA table_info({table})").fetchall()}

    def _migrate_v1_to_v2(self) -> None:
        execution_columns = self._columns("executions")
        if "mode" not in execution_columns:
            self._conn.execute(
                "ALTER TABLE executions ADD COLUMN mode TEXT NOT NULL DEFAULT 'sandbox'"
            )
        if "state" not in execution_columns:
            self._conn.execute(
                "ALTER TABLE executions ADD COLUMN state TEXT NOT NULL DEFAULT 'created'"
            )

        memory_columns = self._columns("memory_items")
        if "category" not in memory_columns:
            self._conn.execute(
                "ALTER TABLE memory_items ADD COLUMN category TEXT NOT NULL DEFAULT 'general'"
            )
        if "knowledge_version" not in memory_columns:
            self._conn.execute(
                "ALTER TABLE memory_items ADD COLUMN knowledge_version TEXT NOT NULL DEFAULT 'unknown'"
            )

    def _migrate_v2_to_v3(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS task_state (
                task_id INTEGER NOT NULL,
                state_key TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(task_id, state_key),
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_goals_priority
                ON goals(status, priority DESC, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_task_state_task
                ON task_state(task_id, state_key);
        """)
        if "goal_id" not in self._columns("tasks"):
            self._conn.execute("ALTER TABLE tasks ADD COLUMN goal_id INTEGER")
        rows = self._conn.execute(
            "SELECT id, goal, status, created_at, updated_at FROM tasks "
            "WHERE goal_id IS NULL ORDER BY id"
        ).fetchall()
        for row in rows:
            goal_status = row["status"] if row["status"] in {"completed", "blocked", "failed"} else "active"
            cur = self._conn.execute(
                "INSERT INTO goals(goal, priority, status, created_at, updated_at) "
                "VALUES (?, 0, ?, ?, ?)",
                (row["goal"], goal_status, row["created_at"], row["updated_at"]),
            )
            self._conn.execute(
                "UPDATE tasks SET goal_id = ? WHERE id = ?",
                (int(cur.lastrowid), row["id"]),
            )

    def create_goal(self, goal: str, priority: int = 0) -> int:
        if not goal or not goal.strip():
            raise ValueError("goal must be a non-empty string")
        now = utc_now()
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO goals(goal, priority, status, created_at, updated_at) "
                "VALUES (?, ?, 'active', ?, ?)",
                (goal, int(priority), now, now),
            )
            return int(cur.lastrowid)

    def get_goal(self, goal_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM goals WHERE id = ?", (goal_id,)
            ).fetchone()
        return dict(row) if row else None

    def set_goal_priority(self, goal_id: int, priority: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE goals SET priority = ?, updated_at = ? WHERE id = ?",
                (int(priority), utc_now(), goal_id),
            )

    def create_task(self, goal: str, priority: int = 0) -> int:
        goal_id = self.create_goal(goal, priority)
        now = utc_now()
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO tasks(goal, goal_id, status, created_at, updated_at) "
                "VALUES (?, ?, 'queued', ?, ?)",
                (goal, goal_id, now, now),
            )
            return int(cur.lastrowid)

    def _sync_goal_status(self, task_id: int, status: str) -> None:
        row = self._conn.execute(
            "SELECT goal_id FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row and row["goal_id"] is not None:
            goal_status = {
                "completed": "completed",
                "blocked": "blocked",
                "failed": "failed",
            }.get(status, "active")
            self._conn.execute(
                "UPDATE goals SET status = ?, updated_at = ? WHERE id = ?",
                (goal_status, utc_now(), row["goal_id"]),
            )

    def update_task(self, task_id: int, status: str, execution_id: int | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE tasks SET status = ?, attempts = attempts + 1, "
                "execution_id = ?, updated_at = ? WHERE id = ?",
                (status, execution_id, utc_now(), task_id),
            )
            self._sync_goal_status(task_id, status)

    def set_task_status(self, task_id: int, status: str, execution_id: int | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE tasks SET status = ?, execution_id = COALESCE(?, execution_id), "
                "updated_at = ? WHERE id = ?",
                (status, execution_id, utc_now(), task_id),
            )
            self._sync_goal_status(task_id, status)

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return dict(row) if row else None

    def set_task_state(self, task_id: int, state_key: str, value: Any) -> int:
        if not state_key:
            raise ValueError("state_key must be non-empty")
        serialized = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
        now = utc_now()
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT version FROM task_state WHERE task_id = ? AND state_key = ?",
                (task_id, state_key),
            ).fetchone()
            version = int(row["version"]) + 1 if row else 1
            self._conn.execute(
                "INSERT INTO task_state(task_id, state_key, version, value, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(task_id, state_key) DO UPDATE SET "
                "version=excluded.version, value=excluded.value, updated_at=excluded.updated_at",
                (task_id, state_key, version, serialized, now),
            )
            return version

    def get_task_state(self, task_id: int, state_key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM task_state WHERE task_id = ? AND state_key = ?",
                (task_id, state_key),
            ).fetchone()
        if row is None:
            return None
        try:
            value = json.loads(row["value"])
        except json.JSONDecodeError:
            value = row["value"]
        return {
            "task_id": row["task_id"],
            "state_key": row["state_key"],
            "version": row["version"],
            "value": value,
            "updated_at": row["updated_at"],
        }

    def create_execution(
        self,
        identity: str,
        goal: str,
        mode: str = "sandbox",
        task_id: int | None = None,
    ) -> int:
        now = utc_now()
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO executions(identity, goal, status, mode, state, created_at) "
                "VALUES (?, ?, 'running', ?, 'running', ?)",
                (identity, goal, mode, now),
            )
            execution_id = int(cur.lastrowid)
            if task_id is not None:
                self._conn.execute(
                    "UPDATE tasks SET execution_id = ?, status = 'running', "
                    "attempts = attempts + 1, updated_at = ? WHERE id = ?",
                    (execution_id, now, task_id),
                )
                self._sync_goal_status(task_id, "running")
            return execution_id

    def update_execution_state(self, execution_id: int, state: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE executions SET state = ? WHERE id = ?",
                (state, execution_id),
            )

    def append_event(self, execution_id: int, sequence: int, stage: str, payload: Any) -> None:
        serialized = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO execution_events(execution_id, sequence, stage, payload, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (execution_id, sequence, stage, serialized, utc_now()),
            )

    def add_memory(
        self,
        store_name: str,
        content: Any,
        provenance: str,
        confidence: float,
        execution_id: int | None = None,
        category: str = "general",
        knowledge_version: str = "unknown",
    ) -> int:
        serialized = content if isinstance(content, str) else json.dumps(content, sort_keys=True)
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO memory_items("
                "execution_id, store_name, content, provenance, confidence, "
                "category, knowledge_version, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    execution_id, store_name, serialized, provenance, float(confidence),
                    category, knowledge_version, utc_now(),
                ),
            )
            return int(cur.lastrowid)

    def search_memory(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        pattern = "%" + query.lower() + "%"
        with self._lock:
            rows = self._conn.execute(
                "SELECT content, provenance, confidence, category, knowledge_version "
                "FROM memory_items WHERE lower(content) LIKE ? "
                "ORDER BY confidence DESC, id DESC LIMIT ?",
                (pattern, int(limit)),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_world_event(self, event: Any, execution_id: int | None = None) -> int:
        serialized = event if isinstance(event, str) else json.dumps(event, sort_keys=True)
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO world_events(execution_id, event, created_at) VALUES (?, ?, ?)",
                (execution_id, serialized, utc_now()),
            )
            return int(cur.lastrowid)

    def get_world_events(self) -> list[Any]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT event FROM world_events ORDER BY id"
            ).fetchall()
        result = []
        for row in rows:
            try:
                result.append(json.loads(row["event"]))
            except json.JSONDecodeError:
                result.append(row["event"])
        return result

    def save_world_snapshot(
        self, snapshot: dict[str, Any], version: int, execution_id: int | None = None
    ) -> int:
        serialized = json.dumps(snapshot, sort_keys=True)
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO world_snapshots(execution_id, version, snapshot, created_at) "
                "VALUES (?, ?, ?, ?)",
                (execution_id, int(version), serialized, utc_now()),
            )
            return int(cur.lastrowid)

    def get_latest_world_snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT version, snapshot FROM world_snapshots "
                "ORDER BY version DESC, id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return {"version": row["version"], "snapshot": json.loads(row["snapshot"])}

    def finish_execution(self, execution_id: int, status: str, verified: bool) -> None:
        state = {"completed": "completed", "blocked": "blocked"}.get(status, "failed")
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE executions SET status = ?, state = ?, verified = ?, completed_at = ? "
                "WHERE id = ?",
                (status, state, int(verified), utc_now(), execution_id),
            )

    def get_execution(self, execution_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM executions WHERE id = ?", (execution_id,)
            ).fetchone()
            if row is None:
                return None
            events = self._conn.execute(
                "SELECT sequence, stage, payload, created_at "
                "FROM execution_events WHERE execution_id = ? ORDER BY sequence",
                (execution_id,),
            ).fetchall()
        return {
            "id": row["id"],
            "identity": row["identity"],
            "goal": row["goal"],
            "status": row["status"],
            "mode": row["mode"],
            "state": row["state"],
            "verified": bool(row["verified"]),
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
            "events": [dict(event) for event in events],
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()
