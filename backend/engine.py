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
        def read_rows(text, fields, name):
            reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff").strip()), strict=True)
            if not reader.fieldnames or set(reader.fieldnames) != set(fields) or len(reader.fieldnames) != len(fields):
                raise ValueError(f"{name} sütunları: {','.join(fields)} olmalıdır.")
            try:
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError(f"{name} satır {reader.line_num}: sütun sayısı geçersiz.")
                    yield {key: value.strip() for key, value in row.items()}
            except csv.Error as exc:
                raise ValueError(f"{name}: geçersiz CSV biçimi.") from exc

        nodes = []
        for row in read_rows(nodes_csv, ("id", "label", "type", "owner", "criticality"), "nodes.csv"):
            if not all(row[key] for key in ("id", "label", "type", "criticality")):
                raise ValueError("Düğüm id, label, type ve criticality alanları boş olamaz.")
            try:
                criticality = int(row["criticality"])
            except ValueError as exc:
                raise ValueError("criticality alanı tam sayı olmalıdır.") from exc
            if not -100 <= criticality <= 100:
                raise ValueError("criticality -100 ile 100 arasında olmalıdır.")
            nodes.append(Node(**{**row, "criticality": criticality}))
        edges = []
        seen = set()
        for row in read_rows(edges_csv, ("source", "target", "relation", "reason"), "edges.csv"):
            if not all(row[key] for key in ("source", "target", "relation")):
                raise ValueError("İlişki source, target ve relation alanları boş olamaz.")
            key = (row["source"], row["target"], row["relation"])
            if key in seen:
                raise ValueError("Aynı source, target ve relation birden fazla kez bulunamaz.")
            seen.add(key)
            edges.append(Edge(**row))
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
                    "status": "İnceleme önerisi",
                    "depth": depth,
                }
            )

        critical_count = sum(item["risk"] == "critical" for item in items)
        evidence_path_count = len(items)
        completeness = sum(bool(item["owner"] and item["reason"]) for item in items)
        metadata_coverage = round(100 * completeness / len(items)) if items else None
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
            note = "Grafikte bu düğümden ilerleyen kayıtlı bir ilişki bulunamadı."

        return {
            "changed_node": changed_node_id,
            "current_value": current_value,
            "proposed_value": proposed_value,
            "summary": summary,
            "note": note,
            "metadata_coverage": metadata_coverage,
            "max_depth": max_depth,
            "impact_count": len(items),
            "critical_count": critical_count,
            "path_count": evidence_path_count,
            "duration_ms": duration_ms,
            "items": items,
        }

