import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from engine import TraceGraph  # noqa: E402
from storage import ProjectStore  # noqa: E402


class ProjectStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database = Path(self.temporary_directory.name) / "nextrace-test.db"
        self.store = ProjectStore(database)
        data = ROOT / "backend" / "data"
        self.graph = TraceGraph.from_csv_files(data / "nodes.csv", data / "edges.csv")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_project_survives_new_store_instance(self):
        self.store.save_project("demo", "Demo", self.graph)
        reopened = ProjectStore(self.store.database_path)
        restored = reopened.load_graph("demo")
        result = restored.analyze("SYS-REQ-142")
        self.assertEqual(result["impact_count"], 8)
        self.assertEqual(reopened.list_projects()[0]["node_count"], 23)
        self.assertEqual(reopened.list_projects()[0]["edge_count"], 20)

    def test_analysis_history_is_persisted(self):
        self.store.save_project("demo", "Demo", self.graph)
        result = self.graph.analyze("SEC-REQ-055", "AES-128", "AES-256")
        analysis_id = self.store.save_analysis("demo", result)
        history = self.store.list_analyses("demo")
        self.assertTrue(analysis_id.startswith("NXT-"))
        self.assertEqual(history[0]["id"], analysis_id)
        self.assertEqual(history[0]["changed_node"], "SEC-REQ-055")

    def test_unknown_project_fails(self):
        with self.assertRaises(KeyError):
            self.store.load_graph("missing")


if __name__ == "__main__":
    unittest.main()
