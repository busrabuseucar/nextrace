"""NexTrace AI MVP: bağımlılıksız HTTP API ve statik web sunucusu."""

from __future__ import annotations

import json
import os
import posixpath
import re
import sys
import threading
import time
from http.cookies import SimpleCookie
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from auth import AuthenticationError, AuthService
from connectors import (
    ConnectorError,
    GitLabConnector,
    JiraConnector,
    build_trace_graph,
    connector_status,
)
from engine import TraceGraph
from storage import ProjectStore


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
DATABASE_PATH = Path(os.environ.get("NEXTRACE_DB_PATH", DATA_DIR / "nextrace.db"))
STORE = ProjectStore(DATABASE_PATH)
AUTH = AuthService(STORE)
MAX_BODY_BYTES = 2 * 1024 * 1024
SESSION_COOKIE = "nextrace_session"
FAILED_LOGINS: dict[str, list[float]] = {}
FAILED_LOGINS_LOCK = threading.Lock()
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 15 * 60
PUBLIC_FILES = {"/", "/index.html", "/styles.css", "/app.js"}
PUBLIC_PREFIXES = ("/assets/", "/docs/")


def ensure_demo_project() -> None:
    if STORE.has_project("demo"):
        return
    graph = TraceGraph.from_csv_files(DATA_DIR / "nodes.csv", DATA_DIR / "edges.csv")
    STORE.save_project(
        "demo", "AQUILA / Uçuş Kontrol Sistemi", graph, source="seed"
    )


ensure_demo_project()


class NexTraceHandler(SimpleHTTPRequestHandler):
    server_version = "NexTrace"
    sys_version = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        super().end_headers()

    def _json(
        self,
        payload: dict,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _session_token(self) -> str | None:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def _current_user(self) -> dict | None:
        return AUTH.authenticate(self._session_token())

    def _require_auth(self) -> dict | None:
        user = self._current_user()
        if not user:
            self._json({"error": "Oturum açılması gerekiyor."}, HTTPStatus.UNAUTHORIZED)
            return None
        if user["must_change_password"]:
            self._json(
                {
                    "error": "Devam etmeden önce geçici parolanı değiştirmelisin.",
                    "code": "PASSWORD_CHANGE_REQUIRED",
                },
                HTTPStatus.FORBIDDEN,
            )
            return None
        return user

    def _require_admin(self, user: dict) -> bool:
        if user["role"] == "admin":
            return True
        self._json({"error": "Bu işlem yönetici yetkisi gerektiriyor."}, HTTPStatus.FORBIDDEN)
        return False

    def _require_project_access(
        self, user: dict, project_id: str, analysis_required: bool = False
    ) -> bool:
        if user["role"] == "admin":
            return True
        access = STORE.get_project_access(project_id, user["id"])
        if not access:
            self._json({"error": "Bu projeye erişim yetkin yok."}, HTTPStatus.FORBIDDEN)
            return False
        if analysis_required and access != "analyst":
            self._json(
                {"error": "Bu projede analiz çalıştırma yetkin yok."},
                HTTPStatus.FORBIDDEN,
            )
            return False
        return True

    def _session_cookie_header(self, token: str, max_age: int = 12 * 60 * 60) -> str:
        secure = "; Secure" if os.environ.get("NEXTRACE_SECURE_COOKIES") == "1" else ""
        return (
            f"{SESSION_COOKIE}={token}; HttpOnly; Path=/; SameSite=Strict; "
            f"Max-Age={max_age}{secure}"
        )

    def _valid_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        if urlparse(origin).netloc == self.headers.get("Host"):
            return True
        self._json({"error": "İstek kaynağı reddedildi."}, HTTPStatus.FORBIDDEN)
        return False

    def _login_allowed(self) -> bool:
        cutoff = time.time() - LOGIN_WINDOW_SECONDS
        address = self.client_address[0]
        with FAILED_LOGINS_LOCK:
            attempts = [stamp for stamp in FAILED_LOGINS.get(address, []) if stamp > cutoff]
            FAILED_LOGINS[address] = attempts
            return len(attempts) < MAX_LOGIN_ATTEMPTS

    def _record_failed_login(self) -> None:
        with FAILED_LOGINS_LOCK:
            FAILED_LOGINS.setdefault(self.client_address[0], []).append(time.time())

    def _clear_failed_logins(self) -> None:
        with FAILED_LOGINS_LOCK:
            FAILED_LOGINS.pop(self.client_address[0], None)

    @staticmethod
    def _public_file_allowed(path: str) -> bool:
        normalized = posixpath.normpath(unquote(path))
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized in PUBLIC_FILES or any(
            normalized.startswith(prefix) for prefix in PUBLIC_PREFIXES
        )

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
        if path == "/api/auth/status":
            user = self._current_user()
            self._json(
                {
                    "setup_required": STORE.user_count() == 0,
                    "authenticated": user is not None,
                    "user": user,
                }
            )
            return
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
            user = self._require_auth()
            if not user:
                return
            projects = STORE.list_projects(None if user["role"] == "admin" else user["id"])
            self._json({"projects": projects})
            return
        if path == "/api/analyses":
            user = self._require_auth()
            if not user:
                return
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
            if not self._require_project_access(user, project_id):
                return
            self._json({"analyses": STORE.list_analyses(project_id, limit)})
            return
        if path == "/api/projects/versions":
            user = self._require_auth()
            if not user:
                return
            project_id = parse_qs(parsed.query).get("project_id", ["demo"])[0].strip()
            if not STORE.has_project(project_id):
                self._json({"error": f"Proje bulunamadı: {project_id}"}, HTTPStatus.NOT_FOUND)
                return
            if not self._require_project_access(user, project_id):
                return
            self._json({"versions": STORE.list_project_versions(project_id)})
            return
        if path == "/api/projects/diff":
            user = self._require_auth()
            if not user:
                return
            query = parse_qs(parsed.query)
            project_id = query.get("project_id", ["demo"])[0].strip()
            from_version = query.get("from_version", [""])[0].strip()
            to_version = query.get("to_version", [""])[0].strip()
            if not from_version or not to_version:
                self._json(
                    {"error": "from_version ve to_version zorunludur."},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            if not STORE.has_project(project_id):
                self._json({"error": f"Proje bulunamadı: {project_id}"}, HTTPStatus.NOT_FOUND)
                return
            if not self._require_project_access(user, project_id):
                return
            try:
                comparison = STORE.compare_project_versions(
                    project_id, from_version, to_version
                )
            except KeyError as exc:
                self._json({"error": str(exc).strip("'")}, HTTPStatus.NOT_FOUND)
                return
            except ValueError as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self._json(comparison)
            return
        if path == "/api/users":
            user = self._require_auth()
            if not user or not self._require_admin(user):
                return
            self._json({"users": STORE.list_users()})
            return
        if path == "/api/projects/access":
            user = self._require_auth()
            if not user or not self._require_admin(user):
                return
            self._json({"memberships": STORE.list_project_access()})
            return
        if path == "/api/connectors/status":
            user = self._require_auth()
            if not user or not self._require_admin(user):
                return
            self._json({"connectors": connector_status()})
            return
        if not self._public_file_allowed(path):
            self._json({"error": "Kaynak bulunamadı."}, HTTPStatus.NOT_FOUND)
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not self._public_file_allowed(path):
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        super().do_HEAD()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not self._valid_origin():
            return
        try:
            payload = self._read_json()
            if path == "/api/auth/setup":
                self._handle_setup(payload)
                return
            if path == "/api/auth/login":
                self._handle_login(payload)
                return
            if path == "/api/auth/logout":
                AUTH.logout(self._session_token())
                self._json(
                    {"message": "Oturum kapatıldı."},
                    extra_headers={"Set-Cookie": self._session_cookie_header("", 0)},
                )
                return
            if path == "/api/auth/password":
                user = self._current_user()
                if not user:
                    self._json(
                        {"error": "Oturum açılması gerekiyor."},
                        HTTPStatus.UNAUTHORIZED,
                    )
                    return
                self._handle_change_password(payload, user)
                return
            user = self._require_auth()
            if not user:
                return
            if path == "/api/analyze":
                self._handle_analyze(payload, user)
                return
            if path == "/api/projects/import":
                if not self._require_admin(user):
                    return
                self._handle_import(payload, user)
                return
            if path == "/api/users":
                if not self._require_admin(user):
                    return
                self._handle_create_user(payload)
                return
            if path == "/api/users/password-reset":
                if not self._require_admin(user):
                    return
                self._handle_admin_password_reset(payload)
                return
            if path == "/api/users/status":
                if not self._require_admin(user):
                    return
                self._handle_user_status(payload)
                return
            if path == "/api/projects/access":
                if not self._require_admin(user):
                    return
                self._handle_project_access(payload)
                return
            if path == "/api/connectors/sync":
                if not self._require_admin(user):
                    return
                self._handle_connector_sync(payload, user)
                return
            self._json({"error": "Uç nokta bulunamadı."}, HTTPStatus.NOT_FOUND)
        except KeyError as exc:
            self._json({"error": str(exc).strip("'")}, HTTPStatus.NOT_FOUND)
        except ConnectorError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
        except (TypeError, ValueError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _handle_setup(self, payload: dict) -> None:
        try:
            token, user, expires_at = AUTH.setup(
                str(payload.get("email", "")), str(payload.get("password", ""))
            )
        except AuthenticationError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._json(
            {"user": user, "expires_at": expires_at},
            HTTPStatus.CREATED,
            {"Set-Cookie": self._session_cookie_header(token)},
        )

    def _handle_login(self, payload: dict) -> None:
        if not self._login_allowed():
            self._json(
                {"error": "Çok fazla başarısız deneme. 15 dakika sonra tekrar dene."},
                HTTPStatus.TOO_MANY_REQUESTS,
            )
            return
        try:
            token, user, expires_at = AUTH.login(
                str(payload.get("email", "")), str(payload.get("password", ""))
            )
        except AuthenticationError as exc:
            self._record_failed_login()
            self._json({"error": str(exc)}, HTTPStatus.UNAUTHORIZED)
            return
        self._clear_failed_logins()
        self._json(
            {"user": user, "expires_at": expires_at},
            extra_headers={"Set-Cookie": self._session_cookie_header(token)},
        )

    def _handle_create_user(self, payload: dict) -> None:
        try:
            user = AUTH.create_user(
                str(payload.get("email", "")),
                str(payload.get("password", "")),
                str(payload.get("role", "analyst")),
            )
        except AuthenticationError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._json({"user": user}, HTTPStatus.CREATED)

    def _handle_change_password(self, payload: dict, user: dict) -> None:
        try:
            token, updated_user, expires_at = AUTH.change_password(
                user["id"],
                str(payload.get("current_password", "")),
                str(payload.get("new_password", "")),
            )
        except AuthenticationError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._json(
            {
                "user": updated_user,
                "expires_at": expires_at,
                "message": "Parolan güncellendi; diğer oturumlar kapatıldı.",
            },
            extra_headers={"Set-Cookie": self._session_cookie_header(token)},
        )

    def _handle_admin_password_reset(self, payload: dict) -> None:
        try:
            user = AUTH.admin_reset_password(
                str(payload.get("user_id", "")).strip(),
                str(payload.get("new_password", "")),
            )
        except AuthenticationError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._json(
            {
                "user": user,
                "message": "Geçici parola atandı; kullanıcının açık oturumları kapatıldı.",
            }
        )

    def _handle_user_status(self, payload: dict) -> None:
        active = payload.get("active")
        if not isinstance(active, bool):
            raise ValueError("active alanı true veya false olmalıdır.")
        user = AUTH.set_user_active(
            str(payload.get("user_id", "")).strip(), active
        )
        self._json(
            {
                "user": user,
                "message": (
                    "Hesap yeniden etkinleştirildi."
                    if active
                    else "Hesap devre dışı bırakıldı; açık oturumları kapatıldı."
                ),
            }
        )

    def _handle_project_access(self, payload: dict) -> None:
        STORE.set_project_access(
            str(payload.get("project_id", "")).strip(),
            str(payload.get("user_id", "")).strip(),
            str(payload.get("access_level", "viewer")).strip(),
        )
        self._json({"message": "Proje erişimi güncellendi."})

    def _handle_analyze(self, payload: dict, user: dict) -> None:
        project_id = str(payload.get("project_id", "demo")).strip()
        changed_node_id = str(payload.get("changed_node_id", "")).strip()
        if not changed_node_id:
            raise ValueError("changed_node_id zorunludur.")
        if not STORE.has_project(project_id):
            raise KeyError(f"Proje bulunamadı: {project_id}")
        if not self._require_project_access(user, project_id, analysis_required=True):
            return
        graph, version = STORE.load_graph_snapshot(project_id)
        result = graph.analyze(
            changed_node_id=changed_node_id,
            current_value=str(payload.get("current_value", "")),
            proposed_value=str(payload.get("proposed_value", "")),
        )
        result.update({"graph_version": version["id"], "graph_version_number": version["version_number"], "created_at": STORE._now(), "created_by": user["id"]})
        analysis_id = STORE.save_analysis(project_id, result)
        self._json({"analysis_id": analysis_id, "project_id": project_id, **result})

    def _handle_import(self, payload: dict, user: dict) -> None:
        project_id = str(payload.get("project_id", "uploaded")).strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", project_id):
            raise ValueError("project_id yalnızca harf, sayı, nokta, tire ve alt çizgi içerebilir.")
        project_name = str(payload.get("name", project_id)).strip()[:120] or project_id
        nodes_csv = payload.get("nodes_csv")
        edges_csv = payload.get("edges_csv")
        if not isinstance(nodes_csv, str) or not isinstance(edges_csv, str):
            raise ValueError("nodes_csv ve edges_csv metin olarak gönderilmelidir.")
        graph = TraceGraph.from_csv_text(nodes_csv, edges_csv)
        version = STORE.save_project(
            project_id,
            project_name,
            graph,
            source="csv",
            created_by=user["id"],
        )
        self._json(
            {
                "project_id": project_id,
                "version": version,
                "node_count": len(graph.nodes),
                "edge_count": sum(len(edges) for edges in graph.adjacency.values()),
                "message": f"Proje grafiğinin v{version['version_number']} sürümü kaydedildi.",
            },
            HTTPStatus.CREATED,
        )

    def _handle_connector_sync(self, payload: dict, user: dict) -> None:
        project_id = str(payload.get("project_id", "")).strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", project_id):
            raise ValueError(
                "project_id yalnızca harf, sayı, nokta, tire ve alt çizgi içerebilir."
            )
        project_name = str(payload.get("name", project_id)).strip()[:120] or project_id
        jira_project_key = str(payload.get("jira_project_key", "")).strip().upper()
        gitlab_project = str(payload.get("gitlab_project", "")).strip()
        if not jira_project_key and not gitlab_project:
            raise ValueError("En az bir Jira proje anahtarı veya GitLab projesi girilmelidir.")
        if jira_project_key and not re.fullmatch(r"[A-Z][A-Z0-9_]{1,19}", jira_project_key):
            raise ValueError("Jira proje anahtarı geçersiz.")
        if gitlab_project and (
            len(gitlab_project) > 240
            or any(ord(character) < 32 for character in gitlab_project)
        ):
            raise ValueError("GitLab proje kimliği veya yolu geçersiz.")

        jira_issues: list[dict] = []
        gitlab_commits: list[dict] = []
        sources: list[str] = []
        if jira_project_key:
            jira_issues = JiraConnector.from_env().list_issues(jira_project_key)
            sources.append("jira")
        if gitlab_project:
            gitlab_commits = GitLabConnector.from_env().list_commits(gitlab_project)
            sources.append("gitlab")

        graph, counts = build_trace_graph(
            jira_issues=jira_issues,
            gitlab_commits=gitlab_commits,
            gitlab_project=gitlab_project,
        )
        version = STORE.save_project(
            project_id,
            project_name,
            graph,
            source="+".join(sources),
            created_by=user["id"],
        )
        self._json(
            {
                "project_id": project_id,
                "version": version,
                **counts,
                "message": (
                    f"Jira/GitLab verisi v{version['version_number']} olarak eşitlendi."
                ),
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
