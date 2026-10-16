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
        self.assertEqual(result["path_count"], 8)
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


class InputRegressionTests(unittest.TestCase):
    nodes = 'id,label,type,owner,criticality\nA,Root,Requirement,,0\nB,Test,Test,QA,1'
    edges = 'source,target,relation,reason\nA,B,tests,'

    def test_malformed_rows_are_validation_errors(self):
        for nodes in ('id,label,type,owner,criticality\nA,short', 'id,label,type,owner,criticality\nA,a,t,o,0,extra', 'id,label,type,owner,criticality\nA,a,t,o,999'):
            with self.subTest(nodes=nodes), self.assertRaises(ValueError):
                TraceGraph.from_csv_text(nodes,self.edges)

    def test_bom_missing_metadata_and_leaf(self):
        graph = TraceGraph.from_csv_text('\ufeff'+self.nodes, self.edges)
        self.assertEqual(graph.analyze('A')['metadata_coverage'],0)
        self.assertIsNone(graph.analyze('B')['metadata_coverage'])

    def test_cycle_terminates_and_duplicate_relation_is_rejected(self):
        graph = TraceGraph.from_csv_text(self.nodes, self.edges+'\nB,A,back,reason')
        self.assertEqual(graph.analyze('A')['impact_count'],1)
        with self.assertRaises(ValueError):
            TraceGraph.from_csv_text(self.nodes,self.edges+'\nA,B,tests,duplicate')
