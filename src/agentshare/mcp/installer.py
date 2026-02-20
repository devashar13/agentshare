"""Auto-inject MCP config into platform configuration files."""

import json
import re
import shutil
import subprocess
from pathlib import Path

from agentshare.config import (
    AGENTS_SKILL_DIR,
    PLATFORM_GLOBAL_RULES,
    PLATFORM_GLOBAL_SKILL_DIRS,
    PLATFORM_MCP_CONFIGS,
    detect_platforms,
)
from agentshare.skills.builtin import (
    AGENTSHARE_CLI_SKILL_CONTENT,
    AGENTSHARE_CLI_SKILL_NAME,
)


def _resolve_executable() -> str:
    """Resolve the full path to the agentshare executable."""
    path = shutil.which("agentshare")
    if path:
        return path
    # Fallback: try common locations
    for candidate in [
        Path.home() / ".local" / "bin" / "agentshare",
        Path("/usr/local/bin/agentshare"),
    ]:
        if candidate.exists():
            return str(candidate)
    # Last resort: use the name and hope it's on PATH at runtime
    return "agentshare"


def _inject_json_config(config_path: Path, executable: str) -> bool:
    """Read/merge/write MCP config into a JSON config file."""
    config: dict = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except (json.JSONDecodeError, OSError):
            config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["agentshare"] = {
        "command": executable,
        "args": ["mcp", "serve"],
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return True


def _install_claude_code(executable: str) -> bool:
    """Install MCP config for Claude Code using the CLI, with JSON fallback."""
    try:
        result = subprocess.run(
            [
                "claude",
                "mcp",
                "add",
                "--scope",
                "user",
                "--transport",
                "stdio",
                "agentshare",
                "--",
                executable,
                "mcp",
                "serve",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # Fallback: write to ~/.claude.json directly
    return _inject_json_config(PLATFORM_MCP_CONFIGS["claude"], executable)


TOML_MARKER_START = "# agentshare:start"
TOML_MARKER_END = "# agentshare:end"


def _inject_toml_config(config_path: Path, executable: str) -> bool:
    """Inject MCP server config into a TOML file (Codex format)."""
    config_path.parent.mkdir(parents=True, exist_ok=True)

    block_lines = [
        TOML_MARKER_START,
        "[mcp_servers.agentshare]",
        f'command = "{executable}"',
        'args = ["mcp", "serve"]',
        TOML_MARKER_END,
    ]
    block = "\n".join(block_lines)

    if config_path.exists():
        text = config_path.read_text()
        start = text.find(TOML_MARKER_START)
        end = text.find(TOML_MARKER_END)
        if start != -1 and end != -1:
            text = text[:start] + block + text[end + len(TOML_MARKER_END) :]
            config_path.write_text(text)
            return True
        separator = "\n\n" if text.strip() else ""
        config_path.write_text(text.rstrip() + separator + block + "\n")
    else:
        config_path.write_text(block + "\n")

    return True


def _remove_toml_config(config_path: Path) -> bool:
    """Remove the agentshare block from a TOML config file."""
    if not config_path.exists():
        return True
    text = config_path.read_text()
    start = text.find(TOML_MARKER_START)
    end = text.find(TOML_MARKER_END)
    if start == -1 or end == -1:
        return True
    before = text[:start].rstrip()
    after = text[end + len(TOML_MARKER_END) :].lstrip()
    separator = "\n\n" if before and after else "\n" if before or after else ""
    cleaned = before + separator + after
    if cleaned.strip():
        config_path.write_text(cleaned)
    else:
        config_path.unlink()
    return True


def _inject_opencode_config(config_path: Path, executable: str) -> bool:
    """Inject MCP server config into an OpenCode jsonc file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config: dict = {}
    if config_path.exists():
        try:
            # Strip comments for JSONC parsing
            text = re.sub(r"//.*$", "", config_path.read_text(), flags=re.MULTILINE)
            config = json.loads(text)
        except (json.JSONDecodeError, OSError):
            config = {}

    if "mcp" not in config:
        config["mcp"] = {}

    config["mcp"]["agentshare"] = {
        "type": "local",
        "command": [executable, "mcp", "serve"],
        "enabled": True,
    }

    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return True


def _remove_opencode_config(config_path: Path) -> bool:
    """Remove the agentshare entry from an OpenCode config file."""
    if not config_path.exists():
        return True
    try:
        text = re.sub(r"//.*$", "", config_path.read_text(), flags=re.MULTILINE)
        config = json.loads(text)
    except (json.JSONDecodeError, OSError):
        return False
    mcp = config.get("mcp", {})
    if "agentshare" in mcp:
        del mcp["agentshare"]
        config_path.write_text(json.dumps(config, indent=2) + "\n")
    return True


RULES_MARKER_START = "<!-- agentshare:start -->"
RULES_MARKER_END = "<!-- agentshare:end -->"

AGENT_INSTRUCTIONS = """\
## AgentShare – Cross-Agent Context Sharing

You have access to AgentShare MCP tools for sharing context across coding agents.

**On session start:**
1. Read the `agentshare-cli` skill before doing anything else.
2. Ask the user: "Do you want me to fetch prior context for this project?"
3. If yes, call `list_sessions` (preferably filtered by `project_path`) to see recent work.
4. If any session looks relevant, use `get_session` to pull full details.
5. If no relevant sessions are found, optionally use `query_context`.
6. Only read project files if MCP context is insufficient to proceed.
7. Briefly tell the user what you found and ask if they want details on any specific session.

**On significant work completion:** Call `write_session` with:
- A short title and summary of what was done
- Key decisions made and why
- Files modified
- Relevant tags (e.g. "bugfix", "refactor", "feature")

**What counts as significant:** Any bug fix, feature addition, refactor, \
architectural decision, or debugging session worth preserving for future agents.\
"""


def _make_marker_block(content: str) -> str:
    """Wrap content in marker comments for idempotent injection."""
    return f"{RULES_MARKER_START}\n{content}\n{RULES_MARKER_END}"


def _inject_marker_block(file_path: Path, content: str) -> bool:
    """Append or replace a marker-delimited block in a file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    block = _make_marker_block(content)

    if file_path.exists():
        text = file_path.read_text()
        start = text.find(RULES_MARKER_START)
        end = text.find(RULES_MARKER_END)
        if start != -1 and end != -1:
            # Replace existing block
            text = text[:start] + block + text[end + len(RULES_MARKER_END) :]
            file_path.write_text(text)
            return True

        # Append with separator
        separator = "\n\n" if text.strip() else ""
        file_path.write_text(text.rstrip() + separator + block + "\n")
    else:
        file_path.write_text(block + "\n")

    return True


def _inject_cursor_rules(file_path: Path, content: str) -> bool:
    """Write a standalone .mdc file with frontmatter for Cursor."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    mdc_content = f"---\nalwaysApply: true\n---\n\n{content}\n"
    file_path.write_text(mdc_content)
    return True


def _write_skill(root_dir: Path, skill_name: str, content: str) -> bool:
    """Write a SKILL.md into a platform skill directory."""
    try:
        skill_dir = root_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content)
        return True
    except OSError:
        return False


def _remove_skill(root_dir: Path, skill_name: str) -> bool:
    """Remove a skill directory from a platform skill directory."""
    try:
        skill_dir = root_dir / skill_name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
        return True
    except OSError:
        return False


def install_cli_skill_global(platforms: list[str]) -> dict[str, bool]:
    """Install the AgentShare CLI skill into global skill dirs."""
    results: dict[str, bool] = {}
    for platform in platforms:
        skill_dir = PLATFORM_GLOBAL_SKILL_DIRS.get(platform)
        if not skill_dir:
            continue
        results[platform] = _write_skill(
            skill_dir,
            AGENTSHARE_CLI_SKILL_NAME,
            AGENTSHARE_CLI_SKILL_CONTENT,
        )

    # Always install into ~/.agents/skills for Codex/OpenCode compatibility
    results["agents"] = _write_skill(
        AGENTS_SKILL_DIR,
        AGENTSHARE_CLI_SKILL_NAME,
        AGENTSHARE_CLI_SKILL_CONTENT,
    )
    return results


def remove_cli_skill_global(platforms: list[str]) -> dict[str, bool]:
    """Remove the AgentShare CLI skill from global skill dirs."""
    results: dict[str, bool] = {}
    for platform in platforms:
        skill_dir = PLATFORM_GLOBAL_SKILL_DIRS.get(platform)
        if not skill_dir:
            continue
        results[platform] = _remove_skill(skill_dir, AGENTSHARE_CLI_SKILL_NAME)

    results["agents"] = _remove_skill(AGENTS_SKILL_DIR, AGENTSHARE_CLI_SKILL_NAME)
    return results


def _inject_agent_rules(platforms: list[str]) -> dict[str, bool]:
    """Inject agent instructions into global rules files for detected platforms."""
    results: dict[str, bool] = {}
    for platform in platforms:
        rules_path = PLATFORM_GLOBAL_RULES.get(platform)
        if not rules_path:
            continue
        try:
            if platform == "cursor":
                results[platform] = _inject_cursor_rules(rules_path, AGENT_INSTRUCTIONS)
            else:
                results[platform] = _inject_marker_block(rules_path, AGENT_INSTRUCTIONS)
        except OSError:
            results[platform] = False
    return results


def _remove_marker_block(file_path: Path) -> bool:
    """Remove the agentshare marker block from a file."""
    if not file_path.exists():
        return True
    text = file_path.read_text()
    start = text.find(RULES_MARKER_START)
    end = text.find(RULES_MARKER_END)
    if start == -1 or end == -1:
        return True
    # Remove block and any surrounding blank lines
    before = text[:start].rstrip()
    after = text[end + len(RULES_MARKER_END) :].lstrip()
    separator = "\n\n" if before and after else "\n" if before or after else ""
    cleaned = before + separator + after
    if cleaned.strip():
        file_path.write_text(cleaned)
    else:
        file_path.unlink()
    return True


def _remove_json_mcp_config(config_path: Path) -> bool:
    """Remove the agentshare entry from a JSON MCP config file."""
    if not config_path.exists():
        return True
    try:
        config = json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    servers = config.get("mcpServers", {})
    if "agentshare" in servers:
        del servers["agentshare"]
        config_path.write_text(json.dumps(config, indent=2) + "\n")
    return True


def remove_mcp_global() -> dict[str, dict[str, bool]]:
    """Remove MCP config, agent rules, and CLI skill from all detected platforms."""
    platforms = detect_platforms()
    mcp_results: dict[str, bool] = {}
    rules_results: dict[str, bool] = {}

    for platform in platforms:
        mcp_ok = True
        rules_ok = True

        # Remove MCP config
        if platform == "codex":
            mcp_ok = _remove_toml_config(PLATFORM_MCP_CONFIGS["codex"])
        elif platform == "opencode":
            continue  # project-scoped only
        elif platform in PLATFORM_MCP_CONFIGS:
            mcp_ok = _remove_json_mcp_config(PLATFORM_MCP_CONFIGS[platform])

        # Remove rules
        rules_path = PLATFORM_GLOBAL_RULES.get(platform)
        if rules_path:
            if platform == "cursor":
                # Standalone file — just delete it
                try:
                    if rules_path.exists():
                        rules_path.unlink()
                    rules_ok = True
                except OSError:
                    rules_ok = False
            else:
                rules_ok = _remove_marker_block(rules_path)

        mcp_results[platform] = mcp_ok
        rules_results[platform] = rules_ok

    skills_results = remove_cli_skill_global(platforms)

    return {"mcp": mcp_results, "rules": rules_results, "skills": skills_results}


def install_mcp_global() -> dict[str, dict[str, bool]]:
    """Install MCP server config and agent rules in all detected platforms.

    Returns {"mcp": {platform: success}, "rules": {platform: success},
    "skills": {platform: success}}.
    """
    executable = _resolve_executable()
    platforms = detect_platforms()
    results: dict[str, bool] = {}

    for platform in platforms:
        if platform == "claude":
            results["claude"] = _install_claude_code(executable)
        elif platform == "codex":
            results["codex"] = _inject_toml_config(
                PLATFORM_MCP_CONFIGS["codex"], executable
            )
        elif platform == "opencode":
            # OpenCode is project-scoped only; skip in global install
            continue
        elif platform in PLATFORM_MCP_CONFIGS:
            results[platform] = _inject_json_config(
                PLATFORM_MCP_CONFIGS[platform], executable
            )

    # Inject agent rules alongside MCP config
    rules_results = _inject_agent_rules(platforms)

    skills_results = install_cli_skill_global(platforms)

    return {"mcp": results, "rules": rules_results, "skills": skills_results}


def install_mcp_project(project_path: Path) -> dict[str, bool]:
    """Install MCP config at project level for all supported formats."""
    executable = _resolve_executable()
    results: dict[str, bool] = {}

    # .mcp.json — Claude Code, Cursor, Windsurf
    results["mcp.json"] = _inject_json_config(
        project_path / ".mcp.json", executable
    )

    # opencode.jsonc — OpenCode
    results["opencode.jsonc"] = _inject_opencode_config(
        project_path / "opencode.jsonc", executable
    )

    return results
