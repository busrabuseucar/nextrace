import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from engine import TraceGraph  # noqa: E402


class TraceGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = ROOT / "backend" / "data"
        cls.graph = TraceGraph.from_csv_files(data / "nodes.csv", data / "edges.csv")

    def test_latency_scenario_is_computed_from_graph(self):
        result = self.graph.analyze("SYS-REQ-142", "250 ms", "150 ms")
        self.assertEqual(result["impact_count"], 8)
        self.assertEqual(result["critical_count"], 3)
        self.assertEqual(result["path_count"], 5)
        self.assertIn("SYS-REQ-142 → INT-017", {item["path"] for item in result["items"]})

    def test_unknown_change_node_fails(self):
        with self.assertRaises(KeyError):
            self.graph.analyze("UNKNOWN")

    def test_csv_import_builds_new_graph(self):
        nodes = "id,label,type,owner,criticality\nREQ-1,Kök,Gereksinim,Ekip,0\nT-1,Test,Test,QA,3\n"
        edges = "source,target,relation,reason\nREQ-1,T-1,doğrular,Kabul testi etkilenir.\n"
        graph = TraceGraph.from_csv_text(nodes, edges)
        result = graph.analyze("REQ-1")
        self.assertEqual(result["impact_count"], 1)
        self.assertEqual(result["items"][0]["id"], "T-1")


if __name__ == "__main__":
    unittest.main()

