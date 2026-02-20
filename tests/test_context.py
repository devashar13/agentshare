"""Tests for context/session storage."""

import pytest

from agentshare.context.models import Session
from agentshare.context.store import SessionStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Create a SessionStore with a temp database."""
    import agentshare.config as config

    db = tmp_path / "test.db"
    skills = tmp_path / "skills"
    skills.mkdir()
    monkeypatch.setattr(config, "AGENTSHARE_DIR", tmp_path)
    monkeypatch.setattr(config, "SKILLS_DIR", skills)
    s = SessionStore(db_path=db)
    yield s
    s.close()


@pytest.fixture
def sample_session():
    return Session(
        agent_source="claude-code",
        project_path="/home/user/myproject",
        title="Added user authentication",
        summary="Implemented JWT-based auth with login/register endpoints. Used bcrypt for password hashing.",
        tags=["auth", "backend"],
        key_decisions=["Chose JWT over sessions for stateless auth"],
        files_modified=["src/auth.py", "src/routes.py"],
    )


class TestSessionStore:
    def test_write_and_get(self, store, sample_session):
        stored = store.write_session(sample_session)
        assert stored.id == sample_session.id

        retrieved = store.get_session(sample_session.id)
        assert retrieved is not None
        assert retrieved.title == "Added user authentication"
        assert retrieved.agent_source == "claude-code"
        assert "auth" in retrieved.tags

    def test_get_nonexistent(self, store):
        assert store.get_session("nonexistent") is None

    def test_list_sessions(self, store):
        for i in range(5):
            store.write_session(
                Session(
                    agent_source="test",
                    project_path="/proj",
                    title=f"Session {i}",
                    summary=f"Did thing {i}",
                )
            )

        sessions = store.list_sessions()
        assert len(sessions) == 5

    def test_list_by_project(self, store):
        store.write_session(
            Session(agent_source="a", project_path="/proj1", title="P1", summary="s1")
        )
        store.write_session(
            Session(agent_source="a", project_path="/proj2", title="P2", summary="s2")
        )

        sessions = store.list_sessions(project_path="/proj1")
        assert len(sessions) == 1
        assert sessions[0].title == "P1"

    def test_query_sessions(self, store, sample_session):
        store.write_session(sample_session)
        store.write_session(
            Session(
                agent_source="cursor",
                project_path="/other",
                title="Fixed CSS layout",
                summary="Resolved flexbox issues in the dashboard",
            )
        )

        results = store.query_sessions("authentication")
        assert len(results) == 1
        assert results[0].title == "Added user authentication"

        results = store.query_sessions("CSS")
        assert len(results) == 1
        assert results[0].title == "Fixed CSS layout"

    def test_query_with_filters(self, store):
        store.write_session(
            Session(
                agent_source="claude-code",
                project_path="/proj",
                title="Auth work",
                summary="Did auth stuff",
            )
        )
        store.write_session(
            Session(
                agent_source="cursor",
                project_path="/proj",
                title="Auth refactor",
                summary="Refactored auth",
            )
        )

        results = store.query_sessions("auth", agent_source="cursor")
        assert len(results) == 1
        assert results[0].agent_source == "cursor"

    def test_delete_session(self, store, sample_session):
        store.write_session(sample_session)
        assert store.delete_session(sample_session.id)
        assert store.get_session(sample_session.id) is None
        assert not store.delete_session("nonexistent")
