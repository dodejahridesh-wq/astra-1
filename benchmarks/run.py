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
