"""NexTrace AI MVP: bağımlılıksız HTTP API ve statik web sunucusu."""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from engine import TraceGraph


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
PROJECTS: dict[str, TraceGraph] = {
    "demo": TraceGraph.from_csv_files(DATA_DIR / "nodes.csv", DATA_DIR / "edges.csv")
}
MAX_BODY_BYTES = 2 * 1024 * 1024


class NexTraceHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Geçersiz Content-Length.") from exc
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("İstek gövdesi boş veya 2 MB sınırını aşıyor.")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Geçerli UTF-8 JSON gönderilmelidir.") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON gövdesi bir nesne olmalıdır.")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json(
                {
                    "status": "ok",
                    "service": "nextrace-mvp",
                    "projects": sorted(PROJECTS),
                    "demo_nodes": len(PROJECTS["demo"].nodes),
                }
            )
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/analyze":
                self._handle_analyze(payload)
                return
            if path == "/api/projects/import":
                self._handle_import(payload)
                return
            self._json({"error": "Uç nokta bulunamadı."}, HTTPStatus.NOT_FOUND)
        except KeyError as exc:
            self._json({"error": str(exc).strip("'")}, HTTPStatus.NOT_FOUND)
        except (TypeError, ValueError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _handle_analyze(self, payload: dict) -> None:
        project_id = str(payload.get("project_id", "demo")).strip()
        changed_node_id = str(payload.get("changed_node_id", "")).strip()
        if not changed_node_id:
            raise ValueError("changed_node_id zorunludur.")
        if project_id not in PROJECTS:
            raise KeyError(f"Proje bulunamadı: {project_id}")
        result = PROJECTS[project_id].analyze(
            changed_node_id=changed_node_id,
            current_value=str(payload.get("current_value", "")),
            proposed_value=str(payload.get("proposed_value", "")),
        )
        self._json({"project_id": project_id, **result})

    def _handle_import(self, payload: dict) -> None:
        project_id = str(payload.get("project_id", "uploaded")).strip()
        if not project_id or len(project_id) > 64:
            raise ValueError("project_id 1-64 karakter arasında olmalıdır.")
        nodes_csv = payload.get("nodes_csv")
        edges_csv = payload.get("edges_csv")
        if not isinstance(nodes_csv, str) or not isinstance(edges_csv, str):
            raise ValueError("nodes_csv ve edges_csv metin olarak gönderilmelidir.")
        graph = TraceGraph.from_csv_text(nodes_csv, edges_csv)
        PROJECTS[project_id] = graph
        self._json(
            {
                "project_id": project_id,
                "node_count": len(graph.nodes),
                "edge_count": sum(len(edges) for edges in graph.adjacency.values()),
                "message": "Proje grafiği başarıyla yüklendi.",
            },
            HTTPStatus.CREATED,
        )

    def log_message(self, format: str, *args) -> None:
        print(f"[NexTrace] {self.address_string()} - {format % args}")


def main() -> None:
    host = "127.0.0.1"
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer((host, port), NexTraceHandler)
    print(f"NexTrace AI MVP: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
