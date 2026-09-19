"""Durable SQLite storage for Astra-1 execution state and provenance."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteStore:
    """Small transactional store for executions, events, memory, and world observations."""

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
            self._conn.executescript(
                """
                PRAGMA foreign_keys = ON;

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
                """
            )
            columns = {
                row["name"]
                for row in self._conn.execute("PRAGMA table_info(executions)").fetchall()
            }
            if "mode" not in columns:
                self._conn.execute(
                    "ALTER TABLE executions ADD COLUMN mode TEXT NOT NULL DEFAULT 'sandbox'"
                )
            if "state" not in columns:
                self._conn.execute(
                    "ALTER TABLE executions ADD COLUMN state TEXT NOT NULL DEFAULT 'created'"
                )

    def create_execution(self, identity: str, goal: str, mode: str = "sandbox") -> int:
        now = utc_now()
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO executions(identity, goal, status, mode, state, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (identity, goal, "running", mode, "running", now),
            )
            return int(cur.lastrowid)

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
                """
                INSERT INTO execution_events(execution_id, sequence, stage, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (execution_id, sequence, stage, serialized, utc_now()),
            )

    def add_memory(
        self,
        store_name: str,
        content: Any,
        provenance: str,
        confidence: float,
        execution_id: int | None = None,
    ) -> int:
        serialized = content if isinstance(content, str) else json.dumps(content, sort_keys=True)
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO memory_items(
                    execution_id, store_name, content, provenance, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (execution_id, store_name, serialized, provenance, float(confidence), utc_now()),
            )
            return int(cur.lastrowid)

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

    def finish_execution(self, execution_id: int, status: str, verified: bool) -> None:
        state = "completed" if status == "completed" else "failed"
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE executions
                SET status = ?, state = ?, verified = ?, completed_at = ?
                WHERE id = ?
                """,
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
                """
                SELECT sequence, stage, payload, created_at
                FROM execution_events
                WHERE execution_id = ?
                ORDER BY sequence
                """,
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
