"""NexTrace AI MVP: bağımlılıksız HTTP API ve statik web sunucusu."""

from __future__ import annotations

import json
import os
import re
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from engine import TraceGraph
from storage import ProjectStore


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
DATABASE_PATH = Path(os.environ.get("NEXTRACE_DB_PATH", DATA_DIR / "nextrace.db"))
STORE = ProjectStore(DATABASE_PATH)
MAX_BODY_BYTES = 2 * 1024 * 1024


def ensure_demo_project() -> None:
    if STORE.has_project("demo"):
        return
    graph = TraceGraph.from_csv_files(DATA_DIR / "nodes.csv", DATA_DIR / "edges.csv")
    STORE.save_project("demo", "AQUILA / Uçuş Kontrol Sistemi", graph)


ensure_demo_project()


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
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            projects = STORE.list_projects()
            demo = next(project for project in projects if project["id"] == "demo")
            self._json(
                {
                    "status": "ok",
                    "service": "nextrace-mvp",
                    "database": "sqlite",
                    "project_count": len(projects),
                    "demo_nodes": demo["node_count"],
                }
            )
            return
        if path == "/api/projects":
            self._json({"projects": STORE.list_projects()})
            return
        if path == "/api/analyses":
            query = parse_qs(parsed.query)
            project_id = query.get("project_id", ["demo"])[0].strip()
            try:
                limit = int(query.get("limit", ["20"])[0])
            except ValueError:
                self._json({"error": "limit tam sayı olmalıdır."}, HTTPStatus.BAD_REQUEST)
                return
            if not STORE.has_project(project_id):
                self._json({"error": f"Proje bulunamadı: {project_id}"}, HTTPStatus.NOT_FOUND)
                return
            self._json({"analyses": STORE.list_analyses(project_id, limit)})
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
        graph = STORE.load_graph(project_id)
        result = graph.analyze(
            changed_node_id=changed_node_id,
            current_value=str(payload.get("current_value", "")),
            proposed_value=str(payload.get("proposed_value", "")),
        )
        analysis_id = STORE.save_analysis(project_id, result)
        self._json({"analysis_id": analysis_id, "project_id": project_id, **result})

    def _handle_import(self, payload: dict) -> None:
        project_id = str(payload.get("project_id", "uploaded")).strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", project_id):
            raise ValueError("project_id yalnızca harf, sayı, nokta, tire ve alt çizgi içerebilir.")
        project_name = str(payload.get("name", project_id)).strip()[:120] or project_id
        nodes_csv = payload.get("nodes_csv")
        edges_csv = payload.get("edges_csv")
        if not isinstance(nodes_csv, str) or not isinstance(edges_csv, str):
            raise ValueError("nodes_csv ve edges_csv metin olarak gönderilmelidir.")
        graph = TraceGraph.from_csv_text(nodes_csv, edges_csv)
        STORE.save_project(project_id, project_name, graph)
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
