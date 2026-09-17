"""NexTrace AI izlenebilirlik grafiği ve dinamik etki analizi motoru."""

from __future__ import annotations

import csv
import io
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    type: str
    owner: str
    criticality: int = 0


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relation: str
    reason: str


class TraceGraph:
    """Yönlü mühendislik varlık grafiği.

    Bir değişiklik düğümünden başlayan genişlik öncelikli tarama ile etkilenen
    varlıkları, kanıt yollarını ve açıklanabilir risk puanlarını üretir.
    """

    def __init__(self, nodes: list[Node], edges: list[Edge]):
        if not nodes:
            raise ValueError("En az bir düğüm gereklidir.")
        self.nodes = {node.id: node for node in nodes}
        if len(self.nodes) != len(nodes):
            raise ValueError("Düğüm kimlikleri benzersiz olmalıdır.")

        self.adjacency: dict[str, list[Edge]] = defaultdict(list)
        for edge in edges:
            if edge.source not in self.nodes or edge.target not in self.nodes:
                raise ValueError(
                    f"Kenar bilinmeyen düğüm içeriyor: {edge.source} -> {edge.target}"
                )
            self.adjacency[edge.source].append(edge)

    @classmethod
    def from_csv_text(cls, nodes_csv: str, edges_csv: str) -> "TraceGraph":
        node_reader = csv.DictReader(io.StringIO(nodes_csv.strip()))
        edge_reader = csv.DictReader(io.StringIO(edges_csv.strip()))
        required_node_fields = {"id", "label", "type", "owner", "criticality"}
        required_edge_fields = {"source", "target", "relation", "reason"}

        if not node_reader.fieldnames or not required_node_fields.issubset(node_reader.fieldnames):
            raise ValueError(
                "nodes.csv sütunları: id,label,type,owner,criticality olmalıdır."
            )
        if not edge_reader.fieldnames or not required_edge_fields.issubset(edge_reader.fieldnames):
            raise ValueError(
                "edges.csv sütunları: source,target,relation,reason olmalıdır."
            )

        nodes = []
        for row in node_reader:
            if not row["id"].strip():
                continue
            try:
                criticality = int(row["criticality"] or 0)
            except ValueError as exc:
                raise ValueError("criticality alanı tam sayı olmalıdır.") from exc
            nodes.append(
                Node(
                    id=row["id"].strip(),
                    label=row["label"].strip(),
                    type=row["type"].strip(),
                    owner=row["owner"].strip(),
                    criticality=criticality,
                )
            )

        edges = [
            Edge(
                source=row["source"].strip(),
                target=row["target"].strip(),
                relation=row["relation"].strip(),
                reason=row["reason"].strip(),
            )
            for row in edge_reader
            if row["source"].strip() and row["target"].strip()
        ]
        return cls(nodes, edges)

    @classmethod
    def from_csv_files(cls, nodes_path: Path, edges_path: Path) -> "TraceGraph":
        return cls.from_csv_text(
            nodes_path.read_text(encoding="utf-8-sig"),
            edges_path.read_text(encoding="utf-8-sig"),
        )

    @staticmethod
    def _risk(score: int) -> str:
        if score >= 88:
            return "critical"
        if score >= 75:
            return "high"
        return "medium"

    @staticmethod
    def _status(risk: str) -> str:
        return {
            "critical": "İnceleme gerekli",
            "high": "Atanmadı",
            "medium": "Planlandı",
        }[risk]

    def analyze(
        self,
        changed_node_id: str,
        current_value: str = "",
        proposed_value: str = "",
        max_depth: int = 5,
    ) -> dict:
        started = time.perf_counter()
        if changed_node_id not in self.nodes:
            raise KeyError(f"Düğüm bulunamadı: {changed_node_id}")

        queue = deque([(changed_node_id, [changed_node_id], 0)])
        best_depth = {changed_node_id: 0}
        evidence_reason: dict[str, str] = {}
        paths: dict[str, list[str]] = {}

        while queue:
            node_id, path, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self.adjacency.get(node_id, []):
                next_depth = depth + 1
                if edge.target in path:
                    continue
                if edge.target in best_depth and best_depth[edge.target] <= next_depth:
                    continue
                best_depth[edge.target] = next_depth
                next_path = [*path, edge.target]
                paths[edge.target] = next_path
                evidence_reason[edge.target] = edge.reason
                queue.append((edge.target, next_path, next_depth))

        items = []
        for node_id, depth in sorted(best_depth.items(), key=lambda pair: (pair[1], pair[0])):
            if node_id == changed_node_id:
                continue
            node = self.nodes[node_id]
            score = max(35, min(99, 100 - depth * 10 + node.criticality))
            risk = self._risk(score)
            items.append(
                {
                    "id": node.id,
                    "label": node.label,
                    "type": node.type,
                    "risk": risk,
                    "score": score,
                    "owner": node.owner,
                    "path": " → ".join(paths[node.id]),
                    "reason": evidence_reason[node.id],
                    "status": self._status(risk),
                    "depth": depth,
                }
            )

        critical_count = sum(item["risk"] == "critical" for item in items)
        evidence_path_count = sum(item["risk"] in {"critical", "high"} for item in items)
        completeness = sum(bool(item["owner"] and item["reason"]) for item in items)
        confidence = 70 if not items else min(95, 72 + round(20 * completeness / len(items)))
        duration_ms = max(1, round((time.perf_counter() - started) * 1000))

        if critical_count:
            summary = "Yüksek etkili değişiklik"
            note = (
                f"{critical_count} kritik varlık bulundu. Canlıya alımdan önce ilgili "
                "sahiplerin değişikliği birlikte incelemesi gerekir."
            )
        elif items:
            summary = "Kontrollü değişiklik"
            note = "Kritik risk bulunmadı; yüksek ve orta riskli varlıklar doğrulanmalıdır."
        else:
            summary = "Bağlı etki bulunamadı"
            note = "Grafikte bu düğümden ilerleyen doğrulanmış bir ilişki bulunamadı."

        return {
            "changed_node": changed_node_id,
            "current_value": current_value,
            "proposed_value": proposed_value,
            "summary": summary,
            "note": note,
            "confidence": confidence,
            "impact_count": len(items),
            "critical_count": critical_count,
            "path_count": evidence_path_count,
            "duration_ms": duration_ms,
            "items": items,
        }

