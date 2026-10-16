"""NexTrace AI için SQLite tabanlı kalıcı proje ve analiz deposu."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from engine import Edge, Node, TraceGraph


class ProjectStore:
    def __init__(self, database_path: Path | str):
        self.database_path = str(database_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS nodes (
                    project_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    type TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    criticality INTEGER NOT NULL,
                    PRIMARY KEY (project_id, id),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS edges (
                    project_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    changed_node TEXT NOT NULL,
                    current_value TEXT NOT NULL,
                    proposed_value TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_analyses_project_created
                    ON analyses(project_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash BLOB NOT NULL,
                    password_salt BLOB NOT NULL,
                    password_iterations INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'analyst')),
                    active INTEGER NOT NULL DEFAULT 1,
                    must_change_password INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);

                CREATE TABLE IF NOT EXISTS project_members (
                    project_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    access_level TEXT NOT NULL CHECK(access_level IN ('viewer', 'analyst')),
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, user_id),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS project_versions (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(project_id, version_number),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_project_versions_project_number
                    ON project_versions(project_id, version_number DESC);

                CREATE TABLE IF NOT EXISTS version_nodes (
                    version_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    type TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    criticality INTEGER NOT NULL,
                    PRIMARY KEY (version_id, id),
                    FOREIGN KEY (version_id) REFERENCES project_versions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS version_edges (
                    version_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    FOREIGN KEY (version_id) REFERENCES project_versions(id) ON DELETE CASCADE
                );
                """
            )
            user_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(users)")
            }
            if "active" not in user_columns:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1"
                )
            if "must_change_password" not in user_columns:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0"
                )
            self._backfill_project_versions(connection)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _backfill_project_versions(self, connection: sqlite3.Connection) -> None:
        projects = connection.execute(
            """
            SELECT p.id, p.created_at
            FROM projects p
            WHERE NOT EXISTS (
                SELECT 1 FROM project_versions pv WHERE pv.project_id = p.id
            )
            """
        ).fetchall()
        for project in projects:
            version_id = f"VER-{uuid.uuid4().hex[:12].upper()}"
            connection.execute(
                """
                INSERT INTO project_versions(
                    id, project_id, version_number, source, created_by, created_at
                ) VALUES (?, ?, 1, 'migration', NULL, ?)
                """,
                (version_id, project["id"], project["created_at"]),
            )
            connection.execute(
                """
                INSERT INTO version_nodes(version_id, id, label, type, owner, criticality)
                SELECT ?, id, label, type, owner, criticality
                FROM nodes WHERE project_id = ?
                """,
                (version_id, project["id"]),
            )
            connection.execute(
                """
                INSERT INTO version_edges(version_id, source, target, relation, reason)
                SELECT ?, source, target, relation, reason
                FROM edges WHERE project_id = ?
                """,
                (version_id, project["id"]),
            )

    def has_project(self, project_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        return row is not None

    def save_project(
        self,
        project_id: str,
        name: str,
        graph: TraceGraph,
        source: str = "csv",
        created_by: str | None = None,
    ) -> dict:
        timestamp = self._now()
        edges = [edge for group in graph.adjacency.values() for edge in group]
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO projects(id, name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name = excluded.name, updated_at = excluded.updated_at
                """,
                (project_id, name, timestamp, timestamp),
            )
            version_number = int(
                connection.execute(
                    """
                    SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version
                    FROM project_versions WHERE project_id = ?
                    """,
                    (project_id,),
                ).fetchone()["next_version"]
            )
            version_id = f"VER-{uuid.uuid4().hex[:12].upper()}"
            connection.execute(
                """
                INSERT INTO project_versions(
                    id, project_id, version_number, source, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    project_id,
                    version_number,
                    source[:32] or "csv",
                    created_by,
                    timestamp,
                ),
            )
            connection.execute("DELETE FROM nodes WHERE project_id = ?", (project_id,))
            connection.execute("DELETE FROM edges WHERE project_id = ?", (project_id,))
            connection.executemany(
                """
                INSERT INTO nodes(project_id, id, label, type, owner, criticality)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (project_id, node.id, node.label, node.type, node.owner, node.criticality)
                    for node in graph.nodes.values()
                ],
            )
            connection.executemany(
                """
                INSERT INTO edges(project_id, source, target, relation, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (project_id, edge.source, edge.target, edge.relation, edge.reason)
                    for edge in edges
                ],
            )
            connection.executemany(
                """
                INSERT INTO version_nodes(
                    version_id, id, label, type, owner, criticality
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        version_id,
                        node.id,
                        node.label,
                        node.type,
                        node.owner,
                        node.criticality,
                    )
                    for node in graph.nodes.values()
                ],
            )
            connection.executemany(
                """
                INSERT INTO version_edges(version_id, source, target, relation, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        version_id,
                        edge.source,
                        edge.target,
                        edge.relation,
                        edge.reason,
                    )
                    for edge in edges
                ],
            )
        return {
            "id": version_id,
            "project_id": project_id,
            "version_number": version_number,
            "source": source[:32] or "csv",
            "created_by": created_by,
            "created_at": timestamp,
            "node_count": len(graph.nodes),
            "edge_count": len(edges),
        }

    def load_graph(self, project_id: str) -> TraceGraph:
        return self.load_graph_snapshot(project_id)[0]

    def load_graph_snapshot(self, project_id: str) -> tuple[TraceGraph, dict]:
        with self._connect() as connection:
            connection.execute("BEGIN")
            version = connection.execute(
                "SELECT * FROM project_versions WHERE project_id = ? ORDER BY version_number DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            if not version:
                raise KeyError(f"Proje bulunamadı: {project_id}")
            node_rows = connection.execute(
                "SELECT id, label, type, owner, criticality FROM version_nodes WHERE version_id = ? ORDER BY id",
                (version["id"],),
            ).fetchall()
            edge_rows = connection.execute(
                "SELECT source, target, relation, reason FROM version_edges WHERE version_id = ? ORDER BY rowid",
                (version["id"],),
            ).fetchall()
        return TraceGraph([Node(**dict(row)) for row in node_rows], [Edge(**dict(row)) for row in edge_rows]), dict(version)

    def list_projects(self, user_id: str | None = None) -> list[dict]:
        with self._connect() as connection:
            if user_id:
                rows = connection.execute(
                    """
                    SELECT p.id, p.name, p.created_at, p.updated_at,
                       (SELECT source FROM project_versions latest WHERE latest.project_id = p.id ORDER BY version_number DESC LIMIT 1) AS latest_source,
                           (SELECT COUNT(*) FROM nodes c WHERE c.project_id = p.id) AS node_count,
                           (SELECT COUNT(*) FROM edges c WHERE c.project_id = p.id) AS edge_count,
                           (SELECT COUNT(*) FROM project_versions c WHERE c.project_id = p.id) AS version_count,
                           pm.access_level
                    FROM projects p
                    JOIN project_members pm ON pm.project_id = p.id AND pm.user_id = ?
                    GROUP BY p.id, pm.access_level
                    ORDER BY p.updated_at DESC
                    """,
                    (user_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                SELECT p.id, p.name, p.created_at, p.updated_at,
                       (SELECT source FROM project_versions latest WHERE latest.project_id = p.id ORDER BY version_number DESC LIMIT 1) AS latest_source,
                       (SELECT COUNT(*) FROM nodes c WHERE c.project_id = p.id) AS node_count,
                       (SELECT COUNT(*) FROM edges c WHERE c.project_id = p.id) AS edge_count,
                       (SELECT COUNT(*) FROM project_versions c WHERE c.project_id = p.id) AS version_count
                FROM projects p
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                    """
                ).fetchall()
        return [dict(row) for row in rows]

    def list_project_versions(self, project_id: str) -> list[dict]:
        with self._connect() as connection:
            if not connection.execute(
                "SELECT 1 FROM projects WHERE id = ?", (project_id,)
            ).fetchone():
                raise KeyError(f"Proje bulunamadı: {project_id}")
            rows = connection.execute(
                """
                SELECT pv.id, pv.project_id, pv.version_number, pv.source,
                       pv.created_by, pv.created_at,
                       COALESCE(u.email, 'Sistem') AS created_by_email,
                       (SELECT COUNT(*) FROM version_nodes c WHERE c.version_id = pv.id) AS node_count,
                       (SELECT COUNT(*) FROM version_edges c WHERE c.version_id = pv.id) AS edge_count
                FROM project_versions pv
                LEFT JOIN users u ON u.id = pv.created_by
                WHERE pv.project_id = ?
                GROUP BY pv.id
                ORDER BY pv.version_number DESC
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def compare_project_versions(
        self, project_id: str, from_version_id: str, to_version_id: str
    ) -> dict:
        if from_version_id == to_version_id:
            raise ValueError("Karşılaştırma için iki farklı sürüm seçilmelidir.")
        with self._connect() as connection:
            version_rows = connection.execute(
                """
                SELECT id, project_id, version_number, source, created_at
                FROM project_versions
                WHERE project_id = ? AND id IN (?, ?)
                """,
                (project_id, from_version_id, to_version_id),
            ).fetchall()
            versions = {row["id"]: dict(row) for row in version_rows}
            if from_version_id not in versions or to_version_id not in versions:
                raise KeyError("Seçilen sürümler bu projede bulunamadı.")

            from_nodes = {
                row["id"]: dict(row)
                for row in connection.execute(
                    """
                    SELECT id, label, type, owner, criticality
                    FROM version_nodes WHERE version_id = ?
                    """,
                    (from_version_id,),
                ).fetchall()
            }
            to_nodes = {
                row["id"]: dict(row)
                for row in connection.execute(
                    """
                    SELECT id, label, type, owner, criticality
                    FROM version_nodes WHERE version_id = ?
                    """,
                    (to_version_id,),
                ).fetchall()
            }
            from_edges = {
                (row["source"], row["target"], row["relation"]): dict(row)
                for row in connection.execute(
                    """
                    SELECT source, target, relation, reason
                    FROM version_edges WHERE version_id = ?
                    """,
                    (from_version_id,),
                ).fetchall()
            }
            to_edges = {
                (row["source"], row["target"], row["relation"]): dict(row)
                for row in connection.execute(
                    """
                    SELECT source, target, relation, reason
                    FROM version_edges WHERE version_id = ?
                    """,
                    (to_version_id,),
                ).fetchall()
            }

        node_changes = self._compare_entities(
            from_nodes,
            to_nodes,
            ("label", "type", "owner", "criticality"),
            lambda key: str(key),
        )
        edge_changes = self._compare_entities(
            from_edges,
            to_edges,
            ("reason",),
            lambda key: f"{key[0]} → {key[1]} ({key[2]})",
        )
        summary = {
            "nodes_added": sum(item["change"] == "added" for item in node_changes),
            "nodes_removed": sum(item["change"] == "removed" for item in node_changes),
            "nodes_modified": sum(item["change"] == "modified" for item in node_changes),
            "edges_added": sum(item["change"] == "added" for item in edge_changes),
            "edges_removed": sum(item["change"] == "removed" for item in edge_changes),
            "edges_modified": sum(item["change"] == "modified" for item in edge_changes),
        }
        summary["total_changes"] = sum(summary.values())
        return {
            "project_id": project_id,
            "from_version": versions[from_version_id],
            "to_version": versions[to_version_id],
            "summary": summary,
            "node_changes": node_changes,
            "edge_changes": edge_changes,
        }

    @staticmethod
    def _compare_entities(
        before: dict,
        after: dict,
        comparable_fields: tuple[str, ...],
        identity_label,
    ) -> list[dict]:
        changes: list[dict] = []
        before_keys = set(before)
        after_keys = set(after)
        for key in sorted(after_keys - before_keys, key=str):
            changes.append(
                {
                    "change": "added",
                    "identity": identity_label(key),
                    "fields": list(comparable_fields),
                    "before": None,
                    "after": after[key],
                }
            )
        for key in sorted(before_keys - after_keys, key=str):
            changes.append(
                {
                    "change": "removed",
                    "identity": identity_label(key),
                    "fields": list(comparable_fields),
                    "before": before[key],
                    "after": None,
                }
            )
        for key in sorted(before_keys & after_keys, key=str):
            fields = [
                field
                for field in comparable_fields
                if before[key][field] != after[key][field]
            ]
            if fields:
                changes.append(
                    {
                        "change": "modified",
                        "identity": identity_label(key),
                        "fields": fields,
                        "before": before[key],
                        "after": after[key],
                    }
                )
        return changes

    def save_analysis(self, project_id: str, result: dict) -> str:
        analysis_id = f"NXT-{uuid.uuid4().hex[:12].upper()}"
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analyses(
                    id, project_id, changed_node, current_value,
                    proposed_value, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    project_id,
                    result["changed_node"],
                    result["current_value"],
                    result["proposed_value"],
                    json.dumps(result, ensure_ascii=False),
                    self._now(),
                ),
            )
        return analysis_id

    def list_analyses(self, project_id: str, limit: int = 20) -> list[dict]:
        safe_limit = max(1, min(limit, 100))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, changed_node, current_value,
                       proposed_value, result_json, created_at
                FROM analyses
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, safe_limit),
            ).fetchall()

        analyses = []
        for row in rows:
            result = json.loads(row["result_json"])
            analyses.append(
                {
                    "id": row["id"],
                    "project_id": row["project_id"],
                    "changed_node": row["changed_node"],
                    "current_value": row["current_value"],
                    "proposed_value": row["proposed_value"],
                    "summary": result["summary"],
                    "impact_count": result["impact_count"],
                    "critical_count": result["critical_count"],
                    "created_at": row["created_at"],
                }
            )
        return analyses

    def user_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return int(row["count"])

    def create_first_user(
        self,
        email: str,
        password_hash: bytes,
        password_salt: bytes,
        password_iterations: int,
    ) -> dict:
        user_id = f"USR-{uuid.uuid4().hex[:12].upper()}"
        created_at = self._now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                raise ValueError("İlk yönetici hesabı daha önce oluşturulmuş.")
            connection.execute(
                """
                INSERT INTO users(
                    id, email, password_hash, password_salt,
                    password_iterations, role, created_at
                ) VALUES (?, ?, ?, ?, ?, 'admin', ?)
                """,
                (
                    user_id,
                    email.lower(),
                    password_hash,
                    password_salt,
                    password_iterations,
                    created_at,
                ),
            )
        return {
            "id": user_id,
            "email": email.lower(),
            "role": "admin",
            "active": True,
            "must_change_password": False,
        }

    def get_user_by_email(self, email: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, email, password_hash, password_salt,
                       password_iterations, role, active,
                       must_change_password, created_at
                FROM users WHERE email = ?
                """,
                (email.lower(),),
            ).fetchone()
        return self._normalize_user(row)

    def get_user_by_id(self, user_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, email, password_hash, password_salt,
                       password_iterations, role, active,
                       must_change_password, created_at
                FROM users WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
        return self._normalize_user(row)

    @staticmethod
    def _normalize_user(row: sqlite3.Row | None) -> dict | None:
        if not row:
            return None
        user = dict(row)
        user["active"] = bool(user["active"])
        user["must_change_password"] = bool(user["must_change_password"])
        return user

    def create_user(
        self,
        email: str,
        password_hash: bytes,
        password_salt: bytes,
        password_iterations: int,
        role: str,
    ) -> dict:
        if role not in {"admin", "analyst"}:
            raise ValueError("Geçersiz kullanıcı rolü.")
        user_id = f"USR-{uuid.uuid4().hex[:12].upper()}"
        created_at = self._now()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO users(
                        id, email, password_hash, password_salt,
                        password_iterations, role, active,
                        must_change_password, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
                    """,
                    (
                        user_id,
                        email.lower(),
                        password_hash,
                        password_salt,
                        password_iterations,
                        role,
                        created_at,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Bu e-posta adresi zaten kayıtlı.") from exc
        return {
            "id": user_id,
            "email": email.lower(),
            "role": role,
            "active": True,
            "must_change_password": True,
            "created_at": created_at,
        }

    def list_users(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, email, role, active, must_change_password, created_at
                FROM users ORDER BY created_at ASC
                """
            ).fetchall()
        return [self._normalize_user(row) for row in rows]

    def update_user_password(
        self,
        user_id: str,
        password_hash: bytes,
        password_salt: bytes,
        password_iterations: int,
        must_change_password: bool,
    ) -> dict:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            user = connection.execute(
                "SELECT 1 FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not user:
                raise KeyError(f"Kullanıcı bulunamadı: {user_id}")
            connection.execute(
                """
                UPDATE users
                SET password_hash = ?, password_salt = ?, password_iterations = ?,
                    must_change_password = ?
                WHERE id = ?
                """,
                (
                    password_hash,
                    password_salt,
                    password_iterations,
                    int(must_change_password),
                    user_id,
                ),
            )
            connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        updated = self.get_user_by_id(user_id)
        if not updated:
            raise KeyError(f"Kullanıcı bulunamadı: {user_id}")
        return updated

    def set_user_active(self, user_id: str, active: bool) -> dict:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            user = connection.execute(
                "SELECT role, active FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not user:
                raise KeyError(f"Kullanıcı bulunamadı: {user_id}")
            if not active and user["role"] == "admin" and bool(user["active"]):
                active_admins = connection.execute(
                    "SELECT COUNT(*) AS count FROM users WHERE role = 'admin' AND active = 1"
                ).fetchone()["count"]
                if active_admins <= 1:
                    raise ValueError("Son aktif yönetici hesabı devre dışı bırakılamaz.")
            connection.execute(
                "UPDATE users SET active = ? WHERE id = ?", (int(active), user_id)
            )
            if not active:
                connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        updated = self.get_user_by_id(user_id)
        if not updated:
            raise KeyError(f"Kullanıcı bulunamadı: {user_id}")
        return updated

    def set_project_access(self, project_id: str, user_id: str, access_level: str) -> None:
        if access_level not in {"viewer", "analyst"}:
            raise ValueError("Erişim seviyesi viewer veya analyst olmalıdır.")
        with self._connect() as connection:
            if not connection.execute(
                "SELECT 1 FROM projects WHERE id = ?", (project_id,)
            ).fetchone():
                raise KeyError(f"Proje bulunamadı: {project_id}")
            user = connection.execute(
                "SELECT role FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not user:
                raise KeyError(f"Kullanıcı bulunamadı: {user_id}")
            if user["role"] == "admin":
                raise ValueError("Yöneticiler tüm projelere zaten erişebilir.")
            connection.execute(
                """
                INSERT INTO project_members(project_id, user_id, access_level, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id, user_id)
                DO UPDATE SET access_level = excluded.access_level
                """,
                (project_id, user_id, access_level, self._now()),
            )

    def get_project_access(self, project_id: str, user_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT access_level FROM project_members
                WHERE project_id = ? AND user_id = ?
                """,
                (project_id, user_id),
            ).fetchone()
        return str(row["access_level"]) if row else None

    def list_project_access(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT pm.project_id, p.name AS project_name, pm.user_id,
                       u.email, pm.access_level, pm.created_at
                FROM project_members pm
                JOIN projects p ON p.id = pm.project_id
                JOIN users u ON u.id = pm.user_id
                ORDER BY p.name, u.email
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def save_session(
        self, token_hash: str, user_id: str, created_at: str, expires_at: str
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions(token_hash, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (token_hash, user_id, created_at, expires_at),
            )

    def get_session_user(self, token_hash: str, now: str) -> dict | None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
            row = connection.execute(
                """
                SELECT u.id, u.email, u.role, u.active,
                       u.must_change_password, s.expires_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1
                """,
                (token_hash, now),
            ).fetchone()
        return self._normalize_user(row)

    def delete_session(self, token_hash: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
