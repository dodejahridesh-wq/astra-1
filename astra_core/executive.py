"""Time-aware executive tick for Astra-1."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ExecutiveTick:
    tick_id: int
    observed_at: str
    due_intentions: tuple[int, ...]
    dispatched_intentions: tuple[int, ...]
    completed_intentions: tuple[int, ...]
    blocked_intentions: tuple[int, ...]


class TemporalExecutive:
    """Wake the persistent runtime, resolve cues, and dispatch due intentions.

    The executive is deliberately small: cue detection is separated from
    cognitive execution, and execution remains subject to the normal runtime
    governance boundary.
    """

    def __init__(self, runtime):
        self.runtime = runtime

    def tick(
        self,
        *,
        now: str | None = None,
        event_cues: Iterable[str] = (),
        dispatch: bool = True,
        limit: int = 50,
    ) -> ExecutiveTick:
        observed_at = now or self.runtime.now()
        intentions = list(
            self.runtime.poll_intentions(
                "time",
                now=observed_at,
                limit=limit,
            )
        )
        for cue in event_cues:
            intentions.extend(
                self.runtime.poll_intentions(
                    "event",
                    cue,
                    now=observed_at,
                    limit=limit,
                )
            )

        # De-duplicate while preserving priority/order returned by the store.
        unique: dict[int, dict[str, Any]] = {}
        for intention in intentions:
            unique.setdefault(int(intention["id"]), intention)

        due_ids = tuple(unique)
        dispatched: list[int] = []
        completed: list[int] = []
        blocked: list[int] = []

        if dispatch:
            for intention_id, intention in unique.items():
                task_id = intention.get("task_id")
                if task_id is not None:
                    task = self.runtime.store.get_task(int(task_id))
                    if task and task["status"] not in {"completed", "blocked", "failed"}:
                        result = self.runtime.resume_task(task_id)
                    else:
                        result = self.runtime.run(
                            intention["description"],
                            task_id=task_id,
                        )
                else:
                    result = self.runtime.run(intention["description"])

                dispatched.append(intention_id)
                if result["status"] == "completed":
                    self.runtime.complete_intention(
                        intention_id, result.get("execution_id")
                    )
                    completed.append(intention_id)
                else:
                    self.runtime.store.set_intention_status(
                        intention_id,
                        "blocked",
                        execution_id=result.get("execution_id"),
                    )
                    blocked.append(intention_id)

        tick_id = self.runtime.store.record_executive_tick(
            observed_at,
            due_ids,
            tuple(dispatched),
            tuple(completed),
            tuple(blocked),
        )
        return ExecutiveTick(
            tick_id,
            observed_at,
            due_ids,
            tuple(dispatched),
            tuple(completed),
            tuple(blocked),
        )
