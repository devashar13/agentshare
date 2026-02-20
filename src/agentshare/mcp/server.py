"""MCP server with context-sharing tools."""

from mcp.server.fastmcp import FastMCP

from agentshare.context.models import Session
from agentshare.context.store import SessionStore

mcp = FastMCP("agentshare")
store = SessionStore()


@mcp.tool()
def write_session(
    agent_source: str,
    project_path: str,
    title: str,
    summary: str,
    tags: list[str] | None = None,
    key_decisions: list[str] | None = None,
    files_modified: list[str] | None = None,
) -> dict:
    """Store a session summary for cross-agent context sharing.

    Call this at the end of a coding session or when switching contexts to preserve
    knowledge for future sessions across any AI agent (Claude Code, Cursor, Windsurf, etc.).

    Args:
        agent_source: Which agent is writing (e.g. "claude-code", "cursor", "windsurf")
        project_path: Absolute path to the project being worked on
        title: Short title summarizing what was done (e.g. "Added user auth with JWT")
        summary: Detailed summary of changes, decisions, and context
        tags: Optional tags for categorization (e.g. ["auth", "backend", "security"])
        key_decisions: Important decisions made during the session
        files_modified: List of files that were changed
    """
    session = Session(
        agent_source=agent_source,
        project_path=project_path,
        title=title,
        summary=summary,
        tags=tags or [],
        key_decisions=key_decisions or [],
        files_modified=files_modified or [],
    )
    result = store.write_session(session)
    return {"id": result.id, "status": "saved", "title": result.title}


@mcp.tool()
def query_context(
    query: str,
    project_path: str | None = None,
    agent_source: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search past session summaries across all AI agents.

    Call this when starting work on a project to understand what was done previously
    by any agent (Claude Code, Cursor, Windsurf, etc.). Searches across titles and
    summaries using full-text search.

    Args:
        query: Search text to find relevant sessions
        project_path: Optional - filter to a specific project
        agent_source: Optional - filter to a specific agent
        limit: Maximum results to return (default 10)
    """
    sessions = store.query_sessions(
        query=query,
        project_path=project_path,
        agent_source=agent_source,
        limit=limit,
    )
    return [
        {
            "id": s.id,
            "agent_source": s.agent_source,
            "project_path": s.project_path,
            "title": s.title,
            "summary": s.summary,
            "tags": s.tags,
            "key_decisions": s.key_decisions,
            "files_modified": s.files_modified,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


@mcp.tool()
def list_sessions(
    project_path: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Browse recent session summaries across all AI agents.

    Returns the most recent sessions, optionally filtered by project path.
    Use this to get an overview of recent work across all agents.

    Args:
        project_path: Optional - filter to a specific project
        limit: Maximum results to return (default 20)
    """
    sessions = store.list_sessions(project_path=project_path, limit=limit)
    return [
        {
            "id": s.id,
            "agent_source": s.agent_source,
            "project_path": s.project_path,
            "title": s.title,
            "summary": s.summary[:200] + ("..." if len(s.summary) > 200 else ""),
            "tags": s.tags,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


@mcp.tool()
def get_session(session_id: str) -> dict | str:
    """Get full details of a specific session by ID.

    Use this after finding a relevant session via query_context or list_sessions
    to get the complete summary, decisions, and file changes.

    Args:
        session_id: The session ID to retrieve
    """
    session = store.get_session(session_id)
    if not session:
        return f"Session {session_id} not found"
    return {
        "id": session.id,
        "agent_source": session.agent_source,
        "project_path": session.project_path,
        "title": session.title,
        "summary": session.summary,
        "tags": session.tags,
        "key_decisions": session.key_decisions,
        "files_modified": session.files_modified,
        "created_at": session.created_at.isoformat(),
        "metadata": session.metadata,
    }
