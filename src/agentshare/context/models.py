"""Session data models for context sharing."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class Session(BaseModel):
    """A session summary from an AI agent."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    agent_source: str = Field(description="Agent that created this session (e.g. claude-code, cursor, windsurf)")
    project_path: str = Field(description="Absolute path to the project")
    title: str = Field(description="Short title summarizing the session")
    summary: str = Field(description="Condensed summary of what was done")
    tags: list[str] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)
