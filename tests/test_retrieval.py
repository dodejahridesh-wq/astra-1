import tempfile
import unittest
from pathlib import Path

from astra_core.retrieval import SQLiteMemoryRetriever
from astra_core.storage import SQLiteStore


class DurableRetrievalTests(unittest.TestCase):
    def test_memory_is_retrievable_after_store_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "astra.db"
            store = SQLiteStore(path)
            store.add_memory(
                "semantic",
                "Astra persistent cognitive architecture",
                "research-note",
                .91,
                category="architecture",
                knowledge_version="v1",
            )
            store.close()

            reopened = SQLiteStore(path)
            results = SQLiteMemoryRetriever(reopened).retrieve("cognitive")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].provenance, "research-note")
            self.assertEqual(results[0].category, "architecture")
            self.assertEqual(results[0].knowledge_version, "v1")
            self.assertAlmostEqual(results[0].confidence, .91)
            reopened.close()


if __name__ == "__main__":
    unittest.main()
