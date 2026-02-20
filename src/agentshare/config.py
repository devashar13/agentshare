"""Configuration and directory management for AgentShare."""

from pathlib import Path

AGENTSHARE_DIR = Path.home() / ".agentshare"
SKILLS_DIR = AGENTSHARE_DIR / "skills"
DB_PATH = AGENTSHARE_DIR / "context.db"
AGENTS_SKILL_DIR = Path.home() / ".agents" / "skills"

# Platform skill directory mappings
PLATFORM_SKILL_DIRS = {
    "claude": ".claude/skills",
    "cursor": ".cursor/skills",
    "windsurf": ".windsurf/skills",
}

# Platform global skill directories
PLATFORM_GLOBAL_SKILL_DIRS = {
    "claude": Path.home() / ".claude" / "skills",
    "cursor": Path.home() / ".cursor" / "skills",
    "windsurf": Path.home() / ".codeium" / "windsurf" / "skills",
    "codex": AGENTS_SKILL_DIR,
    "opencode": Path.home() / ".config" / "opencode" / "skills",
}

# Platform global rules locations (for agent instructions)
PLATFORM_GLOBAL_RULES = {
    "claude": Path.home() / ".claude" / "CLAUDE.md",
    "cursor": Path.home() / ".cursor" / "rules" / "agentshare.mdc",
    "windsurf": Path.home() / ".codeium" / "windsurf" / "memories" / "global_rules.md",
    # codex has no documented global rules mechanism
    # opencode uses AGENTS.md but it's project-scoped
}

# Platform MCP config paths (global)
PLATFORM_MCP_CONFIGS = {
    "claude": Path.home() / ".claude.json",
    "cursor": Path.home() / ".cursor" / "mcp.json",
    "windsurf": Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
    "codex": Path.home() / ".codex" / "config.toml",
}

# Platform detection markers
PLATFORM_MARKERS = {
    "claude": [Path.home() / ".claude.json", Path.home() / ".claude"],
    "cursor": [Path.home() / ".cursor"],
    "windsurf": [Path.home() / ".codeium" / "windsurf"],
    "codex": [Path.home() / ".codex"],
    "opencode": [Path.home() / ".local" / "share" / "opencode"],
}


def ensure_dirs() -> None:
    """Ensure the AgentShare directory structure exists."""
    AGENTSHARE_DIR.mkdir(parents=True, exist_ok=True)
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)


def detect_platforms() -> list[str]:
    """Detect which AI coding platforms are installed."""
    detected = []
    for platform, markers in PLATFORM_MARKERS.items():
        if any(m.exists() for m in markers):
            detected.append(platform)
    return detected
