"""Built-in skills shipped with AgentShare."""

AGENTSHARE_CLI_SKILL_NAME = "agentshare-cli"

AGENTSHARE_CLI_SKILL_CONTENT = """\
---
name: agentshare-cli
description: >
  Use the AgentShare MCP tools to share context across AI coding agents.
  Activate when starting a session, saving work summaries, or when the user
  says 'fetch context', 'save session', 'prior work', or 'what was done before'.
---

# AgentShare MCP Tools

AgentShare provides four MCP tools for cross-agent context sharing. Use them to
retrieve prior work and save summaries so the next agent (or session) picks up
where you left off.

## Tools Reference

### `write_session` — Save a work summary

Call this after completing significant work (bug fixes, features, refactors,
architectural decisions).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_source` | string | yes | Your agent name (e.g. `"claude-code"`, `"cursor"`) |
| `project_path` | string | yes | Absolute path to the project root |
| `title` | string | yes | Short title (e.g. `"Added JWT auth to API"`) |
| `summary` | string | yes | What was done, why, and any important context |
| `tags` | string[] | no | Categorization (e.g. `["auth", "backend"]`) |
| `key_decisions` | string[] | no | Important choices and their rationale |
| `files_modified` | string[] | no | List of changed file paths |

### `list_sessions` — Browse recent sessions

Returns sessions in reverse chronological order.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_path` | string | no | Filter to a specific project |
| `limit` | int | no | Max results (default 20) |

### `get_session` — Get full session details

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | yes | The session ID from `list_sessions` or `query_context` |

### `query_context` — Full-text search across sessions

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Search text (matches titles and summaries) |
| `project_path` | string | no | Filter to a specific project |
| `agent_source` | string | no | Filter to a specific agent |
| `limit` | int | no | Max results (default 10) |

## Examples

### Starting a session
1. Call `list_sessions` filtered by the current `project_path`.
2. If relevant sessions exist, call `get_session` on the most recent one.
3. If nothing relevant appears, try `query_context` with keywords about the task.
4. Summarize what you found to the user before proceeding.

### Saving your work
After completing a feature, bug fix, or refactor:
```
write_session(
  agent_source="claude-code",
  project_path="/Users/me/myproject",
  title="Fixed race condition in webhook handler",
  summary="The /webhooks endpoint was processing events concurrently without
    locking. Added an asyncio.Lock per webhook ID to serialize processing.
    Root cause was the move to async handlers in v2.1.",
  tags=["bugfix", "webhooks", "concurrency"],
  key_decisions=["Per-ID lock instead of global lock for better throughput"],
  files_modified=["src/webhooks/handler.py", "tests/test_webhooks.py"]
)
```

## Troubleshooting

### MCP tools not available
The MCP server may not be registered. Ask the user to run:
`agentshare mcp init --global`

### No sessions found for a project
- Verify the `project_path` is the absolute path to the project root.
- Try `query_context` with broader search terms.
- Sessions may not have been saved yet — this is expected for new projects.
"""
