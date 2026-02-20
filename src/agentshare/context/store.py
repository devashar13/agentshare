"""SQLite session storage with FTS5 search."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from agentshare.config import DB_PATH, ensure_dirs
from agentshare.context.models import Session

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_source TEXT NOT NULL,
    project_path TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    key_decisions TEXT NOT NULL DEFAULT '[]',
    files_modified TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_path);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);

CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
    id UNINDEXED,
    title,
    summary,
    content=sessions,
    content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
    INSERT INTO sessions_fts(rowid, id, title, summary)
    VALUES (new.rowid, new.id, new.title, new.summary);
END;

CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, id, title, summary)
    VALUES ('delete', old.rowid, old.id, old.title, old.summary);
END;

CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, id, title, summary)
    VALUES ('delete', old.rowid, old.id, old.title, old.summary);
    INSERT INTO sessions_fts(rowid, id, title, summary)
    VALUES (new.rowid, new.id, new.title, new.summary);
END;
"""


class SessionStore:
    """SQLite-backed session storage."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            ensure_dirs()
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(SCHEMA)
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"],
            agent_source=row["agent_source"],
            project_path=row["project_path"],
            title=row["title"],
            summary=row["summary"],
            tags=json.loads(row["tags"]),
            key_decisions=json.loads(row["key_decisions"]),
            files_modified=json.loads(row["files_modified"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"]),
        )

    def write_session(self, session: Session) -> Session:
        """Store a session summary."""
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO sessions
            (id, agent_source, project_path, title, summary, tags, key_decisions, files_modified, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session.id,
                session.agent_source,
                session.project_path,
                session.title,
                session.summary,
                json.dumps(session.tags),
                json.dumps(session.key_decisions),
                json.dumps(session.files_modified),
                session.created_at.isoformat(),
                json.dumps(session.metadata),
            ),
        )
        conn.commit()
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return self._row_to_session(row) if row else None

    def list_sessions(
        self,
        project_path: str | None = None,
        limit: int = 20,
    ) -> list[Session]:
        """List recent sessions, optionally filtered by project."""
        conn = self._get_conn()
        if project_path:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE project_path = ? ORDER BY created_at DESC LIMIT ?",
                (project_path, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def query_sessions(
        self,
        query: str,
        project_path: str | None = None,
        agent_source: str | None = None,
        limit: int = 10,
    ) -> list[Session]:
        """Full-text search across sessions."""
        conn = self._get_conn()

        # Build query with FTS
        sql = """
            SELECT s.* FROM sessions s
            JOIN sessions_fts fts ON s.id = fts.id
            WHERE sessions_fts MATCH ?
        """
        params: list = [query]

        if project_path:
            sql += " AND s.project_path = ?"
            params.append(project_path)
        if agent_source:
            sql += " AND s.agent_source = ?"
            params.append(agent_source)

        sql += " ORDER BY s.created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_session(r) for r in rows]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cursor.rowcount > 0
