import sys
import sqlite3
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

    def test_project_versions_are_preserved_and_compared(self):
        first = self.store.save_project("demo", "Demo", self.graph, source="seed")
        data = ROOT / "backend" / "data"
        nodes_csv = (data / "nodes.csv").read_text(encoding="utf-8")
        nodes_csv = nodes_csv.replace(
            "INT-017,Telemetri API sözleşmesi,",
            "INT-017,Telemetri API sözleşmesi v2,",
        )
        nodes_csv += "\nNEW-001,Yeni izleme testi,Test,Doğrulama,2\n"
        edges_csv = (data / "edges.csv").read_text(encoding="utf-8")
        edges_csv += (
            "\nSYS-REQ-142,NEW-001,doğrulanır,"
            "Yeni kabul kriteri bu testte doğrulanır.\n"
        )
        second_graph = TraceGraph.from_csv_text(nodes_csv, edges_csv)
        second = self.store.save_project("demo", "Demo", second_graph, source="csv")

        versions = self.store.list_project_versions("demo")
        self.assertEqual([item["version_number"] for item in versions], [2, 1])
        self.assertEqual(versions[0]["node_count"], 24)
        comparison = self.store.compare_project_versions(
            "demo", first["id"], second["id"]
        )
        self.assertEqual(comparison["summary"]["nodes_added"], 1)
        self.assertEqual(comparison["summary"]["nodes_modified"], 1)
        self.assertEqual(comparison["summary"]["edges_added"], 1)
        self.assertEqual(comparison["summary"]["total_changes"], 3)

    def test_existing_project_is_backfilled_as_version_one(self):
        legacy_database = Path(self.temporary_directory.name) / "legacy.db"
        with sqlite3.connect(legacy_database) as connection:
            connection.executescript(
                """
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE nodes (
                    project_id TEXT NOT NULL, id TEXT NOT NULL, label TEXT NOT NULL,
                    type TEXT NOT NULL, owner TEXT NOT NULL, criticality INTEGER NOT NULL,
                    PRIMARY KEY (project_id, id)
                );
                CREATE TABLE edges (
                    project_id TEXT NOT NULL, source TEXT NOT NULL, target TEXT NOT NULL,
                    relation TEXT NOT NULL, reason TEXT NOT NULL
                );
                INSERT INTO projects VALUES ('legacy', 'Eski Proje', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00');
                INSERT INTO nodes VALUES ('legacy', 'REQ-1', 'Gereksinim', 'Gereksinim', 'Sistem', 0);
                """
            )

        migrated = ProjectStore(legacy_database)
        versions = migrated.list_project_versions("legacy")
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["version_number"], 1)
        self.assertEqual(versions[0]["source"], "migration")
        self.assertEqual(versions[0]["node_count"], 1)


if __name__ == "__main__":
    unittest.main()
