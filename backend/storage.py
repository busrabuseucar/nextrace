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
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def has_project(self, project_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        return row is not None

    def save_project(self, project_id: str, name: str, graph: TraceGraph) -> None:
        timestamp = self._now()
        edges = [edge for group in graph.adjacency.values() for edge in group]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO projects(id, name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name = excluded.name, updated_at = excluded.updated_at
                """,
                (project_id, name, timestamp, timestamp),
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

    def load_graph(self, project_id: str) -> TraceGraph:
        with self._connect() as connection:
            node_rows = connection.execute(
                """
                SELECT id, label, type, owner, criticality
                FROM nodes WHERE project_id = ? ORDER BY id
                """,
                (project_id,),
            ).fetchall()
            if not node_rows:
                raise KeyError(f"Proje bulunamadı: {project_id}")
            edge_rows = connection.execute(
                """
                SELECT source, target, relation, reason
                FROM edges WHERE project_id = ? ORDER BY rowid
                """,
                (project_id,),
            ).fetchall()

        nodes = [Node(**dict(row)) for row in node_rows]
        edges = [Edge(**dict(row)) for row in edge_rows]
        return TraceGraph(nodes, edges)

    def list_projects(self, user_id: str | None = None) -> list[dict]:
        with self._connect() as connection:
            if user_id:
                rows = connection.execute(
                    """
                    SELECT p.id, p.name, p.created_at, p.updated_at,
                           COUNT(DISTINCT n.id) AS node_count,
                           COUNT(DISTINCT e.rowid) AS edge_count,
                           pm.access_level
                    FROM projects p
                    JOIN project_members pm ON pm.project_id = p.id AND pm.user_id = ?
                    LEFT JOIN nodes n ON n.project_id = p.id
                    LEFT JOIN edges e ON e.project_id = p.id
                    GROUP BY p.id, pm.access_level
                    ORDER BY p.updated_at DESC
                    """,
                    (user_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                SELECT p.id, p.name, p.created_at, p.updated_at,
                       COUNT(DISTINCT n.id) AS node_count,
                       COUNT(DISTINCT e.rowid) AS edge_count
                FROM projects p
                LEFT JOIN nodes n ON n.project_id = p.id
                LEFT JOIN edges e ON e.project_id = p.id
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                    """
                ).fetchall()
        return [dict(row) for row in rows]

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
        return {"id": user_id, "email": email.lower(), "role": "admin"}

    def get_user_by_email(self, email: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, email, password_hash, password_salt,
                       password_iterations, role, created_at
                FROM users WHERE email = ?
                """,
                (email.lower(),),
            ).fetchone()
        return dict(row) if row else None

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
                        password_iterations, role, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
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
        return {"id": user_id, "email": email.lower(), "role": role, "created_at": created_at}

    def list_users(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, email, role, created_at
                FROM users ORDER BY created_at ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

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
                SELECT u.id, u.email, u.role, s.expires_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ? AND s.expires_at > ?
                """,
                (token_hash, now),
            ).fetchone()
        return dict(row) if row else None

    def delete_session(self, token_hash: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
