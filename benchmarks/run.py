"""Run deterministic Astra-1 cognitive benchmarks."""
import json
import sys
import tempfile
from pathlib import Path

# Allow direct execution from the repository without requiring PYTHONPATH.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astra_core.modes import ExecutionMode
from astra_core.runtime import PersistentRuntime
from astra_core.storage import SQLiteStore


with open(Path(__file__).with_name("cases.json"), encoding="utf-8") as f:
    cases = json.load(f)

with tempfile.TemporaryDirectory() as tmp:
    store = SQLiteStore(Path(tmp) / "benchmark.db")
    runtime = PersistentRuntime(store=store)
    passed = 0

    for case in cases:
        if case["category"] == "prospective-memory":
            intention_id = runtime.create_intention(
                "execute deferred benchmark step",
                "event",
                "benchmark.cue",
                priority=5,
            )
            due = runtime.poll_intentions("event", "benchmark.cue")
            ok = len(due) == 1 and due[0]["id"] == intention_id and due[0]["status"] == "due"
            if ok:
                runtime.complete_intention(intention_id)
                ok = runtime.store.get_intention(intention_id)["status"] == "completed"
            passed += int(ok)
            print(case["id"], "PASS" if ok else "FAIL", "completed" if ok else "failed")
            continue

        if case["category"] == "temporal-executive":
            intention_id = runtime.create_intention(
                "execute temporal benchmark step",
                "event",
                "temporal.cue",
                priority=8,
            )
            tick = runtime.tick(
                now="2026-09-20T10:00:00+00:00",
                event_cues=("temporal.cue",),
            )
            ok = (
                tick.due_intentions == (intention_id,)
                and tick.completed_intentions == (intention_id,)
                and runtime.store.get_intention(intention_id)["status"] == "completed"
            )
            passed += int(ok)
            print(case["id"], "PASS" if ok else "FAIL", "completed" if ok else "failed")
            continue

        if case["category"] == "selective-foresight":
            runtime.record_transition("benchmark.lookup", {"result": "found"})
            runtime.record_transition("benchmark.lookup", {"result": "found"})
            runtime.record_transition("benchmark.lookup", {"result": "missing"})
            prediction = runtime.predict("benchmark.lookup", min_confidence=0.6)
            ok = (
                prediction is not None
                and prediction.predicted_outcome == {"result": "found"}
                and prediction.confidence >= 0.6
            )
            if ok:
                for _ in range(2):
                    runtime.record_prediction_error(
                        "benchmark.lookup",
                        {"result": "found"},
                        {"result": "missing"},
                        prediction_confidence=prediction.confidence,
                    )
                snapshot = runtime.store.get_latest_world_snapshot()
                ok = (
                    len(snapshot["snapshot"]["prediction_errors"]) == 2
                    and len(snapshot["snapshot"]["model_revisions"]) == 1
                    and snapshot["snapshot"]["model_revisions"][0]["mismatch_count"] == 2
                )
            passed += int(ok)
            print(case["id"], "PASS" if ok else "FAIL", "predicted" if ok else "filtered")
            continue

        mode = ExecutionMode.SANDBOX
        if case["category"] == "action-boundary":
            mode = ExecutionMode.LIVE
        result = runtime.run(case["goal"], mode)
        expected = "blocked" if mode is ExecutionMode.LIVE else "completed"
        ok = result["status"] == expected
        passed += int(ok)
        print(case["id"], "PASS" if ok else "FAIL", result["status"])

    print(f"SUMMARY {passed}/{len(cases)}")
    store.close()
