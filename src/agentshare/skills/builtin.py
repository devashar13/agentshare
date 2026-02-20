"""Built-in skills shipped with AgentShare."""

AGENTSHARE_CLI_SKILL_NAME = "agentshare-cli"

AGENTSHARE_CLI_SKILL_CONTENT = """---
name: agentshare-cli
description: Install and use the AgentShare CLI to configure MCP and skills across AI coding agents.
---

# AgentShare CLI

Read this skill before starting work. Use it when you need the `agentshare` CLI or when
MCP/skills setup is failing.

## Behavior

1) Ask the user: "Do you want me to fetch prior context for this project?"
2) If yes, call `list_sessions` (preferably filtered by `project_path`) and then
`get_session` for relevant entries. If no relevant sessions are found, optionally
use `query_context`.
3) Only read project files if MCP context is insufficient to proceed.

## Install

Prefer these options in order, picking what the environment supports:

1) `pipx install agentshare`
2) `uv tool install agentshare`
3) `python -m pip install --user agentshare`

Verify with: `agentshare --version`. If the command is not found, ensure your user bin
directory (for example `~/.local/bin` or the pipx bin dir) is on PATH.

## Common commands

- `agentshare mcp init --global` — install MCP server config + agent rules + this skill
- `agentshare mcp init --path <project>` — project MCP config
- `agentshare mcp serve` — start MCP server (stdio)
- `agentshare mcp remove` — remove MCP config + rules + this skill
- `agentshare skills list|create|add|remove` — manage skills registry
- `agentshare init skills` — scaffold skills into a project
"""
