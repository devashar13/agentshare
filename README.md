# AgentShare

Share skills and context across AI coding agents (Claude Code, Cursor, Windsurf).

AgentShare gives your AI agents **shared memory** — when one agent finishes work, the next one picks up where it left off. It also provides a **skills registry** so you can write reusable instruction snippets once and scaffold them into any project for any platform.

## Quick Start

```bash
pip install agentshare

# Register the MCP server + inject agent rules into all detected platforms
agentshare mcp init --global

# Restart your AI agents to pick up the changes
```

That's it. Your agents will now automatically:
- Ask if you want them to fetch prior context for the project
- Use MCP to fetch prior context when you agree
- Save summaries of their work for future agents (`write_session`)

`agentshare mcp init --global` also installs an `agentshare-cli` skill into each detected
platform's global skill directory plus `~/.agents/skills`. This skill teaches agents how
to install and use the AgentShare CLI.

AgentShare also nudges agents to check recent MCP sessions first and only read files when
the context is insufficient.

## How It Works

AgentShare has two core features:

### 1. Cross-Agent Context Sharing (MCP Server)

An [MCP](https://modelcontextprotocol.io) server exposes four tools to your agents:

| Tool | Purpose |
|------|---------|
| `write_session` | Save a summary of work done — title, decisions, files modified, tags |
| `query_context` | Full-text search across all past sessions |
| `list_sessions` | Browse recent sessions chronologically |
| `get_session` | Fetch full details of a specific session |

Sessions are stored in a local SQLite database (`~/.agentshare/context.db`) with FTS5 full-text search.

### 2. Skills Registry

Skills are reusable Markdown instruction files (with YAML frontmatter) that you manage globally and scaffold into projects per-platform.

```bash
# Create a skill
agentshare skills create code-review --description "Code review checklist" --category workflows

# Edit it
# ~/.agentshare/skills/workflows/code-review/SKILL.md

# Scaffold into a project for all platforms
agentshare init skills --path ./my-project --all-platforms
```

## Supported Platforms

| Platform | MCP Config | Agent Rules | Detection |
|----------|-----------|-------------|-----------|
| Claude Code | `claude mcp add` (fallback: `~/.claude.json`) | `~/.claude/CLAUDE.md` | `~/.claude.json` or `~/.claude/` |
| Cursor | `~/.cursor/mcp.json` | `~/.cursor/rules/agentshare.mdc` | `~/.cursor/` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `~/.codeium/windsurf/memories/global_rules.md` | `~/.codeium/windsurf/` |

Platforms are auto-detected based on the presence of their config directories.

## CLI Reference

```
agentshare --version              Show version

agentshare mcp init --global      Register MCP server + inject agent rules + install CLI skill globally
agentshare mcp init               Write .mcp.json to current project (local install)
agentshare mcp serve              Start MCP server (used internally by platforms)
agentshare mcp remove             Remove MCP config + rules + CLI skill from all platforms

agentshare skills list            List all registered skills
agentshare skills add <path>      Import a skill directory
agentshare skills remove <name>   Remove a skill
agentshare skills create <name>   Create a new skill  [-d description] [-c category]

agentshare init skills            Scaffold skills into a project
                                  [--path] [--platform] [--all-platforms] [--category]
```

## Development

```bash
git clone https://github.com/devashar13/agentshare.git
cd agentshare
uv venv && source .venv/bin/activate
uv pip install ".[dev]"

# Run tests
uv run pytest -v
```

> **Note:** After making code changes, re-run `uv pip install .` to pick them up.

Requires Python 3.11+.

## Architecture

```
~/.agentshare/
  skills/              # Global skills registry
    <category>/<name>/SKILL.md
  context.db           # SQLite + FTS5 session store

src/agentshare/
  cli.py               # Typer CLI app
  config.py            # Paths, platform detection
  context/
    models.py          # Session model (Pydantic)
    store.py           # SQLite CRUD + full-text search
  mcp/
    server.py          # FastMCP server (4 tools)
    installer.py       # Platform config + rules injection
  skills/
    registry.py        # Skill CRUD
    scaffold.py        # Copy skills into project dirs
```

## License

MIT
