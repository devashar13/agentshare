"""Tests for MCP server tools."""

import pytest

from agentshare.context.store import SessionStore


@pytest.fixture(autouse=True)
def mock_store(tmp_path, monkeypatch):
    """Replace the MCP server's store with a temp one."""
    import agentshare.config as config

    db = tmp_path / "test.db"
    skills = tmp_path / "skills"
    skills.mkdir()
    monkeypatch.setattr(config, "AGENTSHARE_DIR", tmp_path)
    monkeypatch.setattr(config, "SKILLS_DIR", skills)
    store = SessionStore(db_path=db)

    import agentshare.mcp.server as server_mod

    monkeypatch.setattr(server_mod, "store", store)
    yield store
    store.close()


class TestMCPTools:
    def test_write_session(self):
        from agentshare.mcp.server import write_session

        result = write_session(
            agent_source="claude-code",
            project_path="/test/project",
            title="Test session",
            summary="Did some testing",
            tags=["test"],
        )
        assert result["status"] == "saved"
        assert result["title"] == "Test session"
        assert "id" in result

    def test_query_context(self):
        from agentshare.mcp.server import query_context, write_session

        write_session(
            agent_source="cursor",
            project_path="/proj",
            title="Database migration",
            summary="Migrated from MySQL to PostgreSQL",
        )

        results = query_context(query="database")
        assert len(results) == 1
        assert results[0]["title"] == "Database migration"

    def test_list_sessions(self):
        from agentshare.mcp.server import list_sessions, write_session

        write_session(
            agent_source="a", project_path="/p", title="S1", summary="Sum1"
        )
        write_session(
            agent_source="b", project_path="/p", title="S2", summary="Sum2"
        )

        results = list_sessions()
        assert len(results) == 2

    def test_get_session(self):
        from agentshare.mcp.server import get_session, write_session

        result = write_session(
            agent_source="windsurf",
            project_path="/proj",
            title="Get me",
            summary="Full details here",
            key_decisions=["Decision 1"],
            files_modified=["file.py"],
        )

        session = get_session(result["id"])
        assert isinstance(session, dict)
        assert session["title"] == "Get me"
        assert session["key_decisions"] == ["Decision 1"]

    def test_get_session_not_found(self):
        from agentshare.mcp.server import get_session

        result = get_session("nonexistent")
        assert isinstance(result, str)
        assert "not found" in result
