"""Tests for MCP installer."""

import json

import pytest

from agentshare.mcp.installer import (
    AGENT_INSTRUCTIONS,
    RULES_MARKER_END,
    RULES_MARKER_START,
    TOML_MARKER_END,
    TOML_MARKER_START,
    _inject_cursor_rules,
    _inject_json_config,
    _inject_marker_block,
    _inject_opencode_config,
    _inject_toml_config,
    _remove_json_mcp_config,
    _remove_marker_block,
    _remove_opencode_config,
    _remove_toml_config,
    install_cli_skill_global,
    install_mcp_global,
    install_mcp_project,
    remove_cli_skill_global,
)
from agentshare.skills.builtin import (
    AGENTSHARE_CLI_SKILL_CONTENT,
    AGENTSHARE_CLI_SKILL_NAME,
)


class TestInjectJsonConfig:
    def test_creates_new_config(self, tmp_path):
        config_path = tmp_path / "mcp.json"
        _inject_json_config(config_path, "/usr/bin/agentshare")

        config = json.loads(config_path.read_text())
        assert "mcpServers" in config
        assert config["mcpServers"]["agentshare"]["command"] == "/usr/bin/agentshare"
        assert config["mcpServers"]["agentshare"]["args"] == ["mcp", "serve"]

    def test_merges_existing_config(self, tmp_path):
        config_path = tmp_path / "mcp.json"
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "other-server": {"command": "other", "args": ["run"]}
                    }
                }
            )
        )

        _inject_json_config(config_path, "/usr/bin/agentshare")

        config = json.loads(config_path.read_text())
        assert "other-server" in config["mcpServers"]
        assert "agentshare" in config["mcpServers"]

    def test_handles_empty_file(self, tmp_path):
        config_path = tmp_path / "mcp.json"
        config_path.write_text("")

        _inject_json_config(config_path, "/usr/bin/agentshare")
        config = json.loads(config_path.read_text())
        assert "agentshare" in config["mcpServers"]

    def test_creates_parent_dirs(self, tmp_path):
        config_path = tmp_path / "nested" / "dir" / "mcp.json"
        _inject_json_config(config_path, "/usr/bin/agentshare")
        assert config_path.exists()


class TestInstallProject:
    def test_creates_mcp_json_and_opencode(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "agentshare.mcp.installer._resolve_executable",
            lambda: "/usr/bin/agentshare",
        )
        results = install_mcp_project(tmp_path)
        assert results["mcp.json"] is True
        assert results["opencode.jsonc"] is True

        config = json.loads((tmp_path / ".mcp.json").read_text())
        assert "agentshare" in config["mcpServers"]

        oc = json.loads((tmp_path / "opencode.jsonc").read_text())
        assert oc["mcp"]["agentshare"]["type"] == "local"


class TestInstallGlobal:
    def test_returns_skills_results(self, tmp_path, monkeypatch):
        claude_root = tmp_path / "claude_skills"
        agents_root = tmp_path / "agents_skills"

        monkeypatch.setattr(
            "agentshare.mcp.installer.detect_platforms",
            lambda: ["claude"],
        )
        monkeypatch.setattr(
            "agentshare.mcp.installer.PLATFORM_GLOBAL_SKILL_DIRS",
            {"claude": claude_root},
        )
        monkeypatch.setattr(
            "agentshare.mcp.installer.AGENTS_SKILL_DIR",
            agents_root,
        )
        monkeypatch.setattr(
            "agentshare.mcp.installer._install_claude_code",
            lambda executable: True,
        )
        monkeypatch.setattr(
            "agentshare.mcp.installer._inject_agent_rules",
            lambda platforms: {"claude": True},
        )

        results = install_mcp_global()
        assert "skills" in results
        assert results["skills"]["claude"] is True
        assert results["skills"]["agents"] is True


class TestInjectMarkerBlock:
    def test_creates_new_file(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        _inject_marker_block(path, "test content")

        text = path.read_text()
        assert RULES_MARKER_START in text
        assert RULES_MARKER_END in text
        assert "test content" in text

    def test_appends_to_existing_file(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        path.write_text("# Existing content\n\nSome rules here.\n")

        _inject_marker_block(path, "test content")

        text = path.read_text()
        assert text.startswith("# Existing content")
        assert "test content" in text
        assert text.count(RULES_MARKER_START) == 1

    def test_idempotent_replaces_existing_block(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        _inject_marker_block(path, "first version")
        _inject_marker_block(path, "second version")

        text = path.read_text()
        assert "second version" in text
        assert "first version" not in text
        assert text.count(RULES_MARKER_START) == 1

    def test_preserves_surrounding_content(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        path.write_text("# Before\n\n<!-- agentshare:start -->\nold\n<!-- agentshare:end -->\n\n# After\n")

        _inject_marker_block(path, "new content")

        text = path.read_text()
        assert "# Before" in text
        assert "# After" in text
        assert "new content" in text
        assert "old" not in text

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "rules.md"
        _inject_marker_block(path, "content")
        assert path.exists()


class TestInjectCursorRules:
    def test_writes_mdc_with_frontmatter(self, tmp_path):
        path = tmp_path / "agentshare.mdc"
        _inject_cursor_rules(path, "test content")

        text = path.read_text()
        assert text.startswith("---\nalwaysApply: true\n---")
        assert "test content" in text

    def test_overwrites_on_rerun(self, tmp_path):
        path = tmp_path / "agentshare.mdc"
        _inject_cursor_rules(path, "first")
        _inject_cursor_rules(path, "second")

        text = path.read_text()
        assert "second" in text
        assert "first" not in text


class TestRemoveMarkerBlock:
    def test_removes_block(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        path.write_text("# Before\n\n<!-- agentshare:start -->\ncontent\n<!-- agentshare:end -->\n\n# After\n")

        _remove_marker_block(path)

        text = path.read_text()
        assert RULES_MARKER_START not in text
        assert "# Before" in text
        assert "# After" in text

    def test_deletes_file_if_only_block(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        _inject_marker_block(path, "content")

        _remove_marker_block(path)
        assert not path.exists()

    def test_noop_if_no_file(self, tmp_path):
        path = tmp_path / "nonexistent.md"
        assert _remove_marker_block(path) is True

    def test_noop_if_no_markers(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        path.write_text("# Just a normal file\n")

        _remove_marker_block(path)
        assert path.read_text() == "# Just a normal file\n"


class TestCliSkillInstall:
    def test_installs_skill_into_platform_and_agents(self, tmp_path, monkeypatch):
        claude_root = tmp_path / "claude_skills"
        agents_root = tmp_path / "agents_skills"

        monkeypatch.setattr(
            "agentshare.mcp.installer.PLATFORM_GLOBAL_SKILL_DIRS",
            {"claude": claude_root},
        )
        monkeypatch.setattr(
            "agentshare.mcp.installer.AGENTS_SKILL_DIR",
            agents_root,
        )

        results = install_cli_skill_global(["claude"])
        assert results["claude"] is True
        assert results["agents"] is True

        skill_path = claude_root / AGENTSHARE_CLI_SKILL_NAME / "SKILL.md"
        assert skill_path.read_text() == AGENTSHARE_CLI_SKILL_CONTENT

        agents_skill = agents_root / AGENTSHARE_CLI_SKILL_NAME / "SKILL.md"
        assert agents_skill.exists()

    def test_removes_skill(self, tmp_path, monkeypatch):
        claude_root = tmp_path / "claude_skills"
        agents_root = tmp_path / "agents_skills"

        monkeypatch.setattr(
            "agentshare.mcp.installer.PLATFORM_GLOBAL_SKILL_DIRS",
            {"claude": claude_root},
        )
        monkeypatch.setattr(
            "agentshare.mcp.installer.AGENTS_SKILL_DIR",
            agents_root,
        )

        install_cli_skill_global(["claude"])
        results = remove_cli_skill_global(["claude"])

        assert results["claude"] is True
        assert results["agents"] is True
        assert not (claude_root / AGENTSHARE_CLI_SKILL_NAME).exists()
        assert not (agents_root / AGENTSHARE_CLI_SKILL_NAME).exists()


class TestRemoveJsonMcpConfig:
    def test_removes_agentshare_entry(self, tmp_path):
        path = tmp_path / "mcp.json"
        path.write_text(json.dumps({
            "mcpServers": {
                "agentshare": {"command": "agentshare", "args": ["mcp", "serve"]},
                "other": {"command": "other", "args": []},
            }
        }))

        _remove_json_mcp_config(path)

        config = json.loads(path.read_text())
        assert "agentshare" not in config["mcpServers"]
        assert "other" in config["mcpServers"]

    def test_noop_if_no_file(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        assert _remove_json_mcp_config(path) is True


class TestInjectTomlConfig:
    def test_creates_new_config(self, tmp_path):
        path = tmp_path / "config.toml"
        _inject_toml_config(path, "/usr/bin/agentshare")

        text = path.read_text()
        assert "[mcp_servers.agentshare]" in text
        assert 'command = "/usr/bin/agentshare"' in text
        assert 'args = ["mcp", "serve"]' in text

    def test_appends_to_existing(self, tmp_path):
        path = tmp_path / "config.toml"
        path.write_text('[mcp_servers.other]\ncommand = "other"\n')

        _inject_toml_config(path, "/usr/bin/agentshare")

        text = path.read_text()
        assert "[mcp_servers.other]" in text
        assert "[mcp_servers.agentshare]" in text

    def test_idempotent(self, tmp_path):
        path = tmp_path / "config.toml"
        _inject_toml_config(path, "/usr/bin/agentshare")
        _inject_toml_config(path, "/new/path/agentshare")

        text = path.read_text()
        assert text.count("[mcp_servers.agentshare]") == 1
        assert "/new/path/agentshare" in text
        assert "/usr/bin/agentshare" not in text


class TestRemoveTomlConfig:
    def test_removes_block(self, tmp_path):
        path = tmp_path / "config.toml"
        path.write_text('[mcp_servers.other]\ncommand = "other"\n')
        _inject_toml_config(path, "/usr/bin/agentshare")

        _remove_toml_config(path)

        text = path.read_text()
        assert "[mcp_servers.agentshare]" not in text
        assert "[mcp_servers.other]" in text

    def test_deletes_file_if_only_block(self, tmp_path):
        path = tmp_path / "config.toml"
        _inject_toml_config(path, "/usr/bin/agentshare")

        _remove_toml_config(path)
        assert not path.exists()

    def test_noop_if_no_file(self, tmp_path):
        path = tmp_path / "nonexistent.toml"
        assert _remove_toml_config(path) is True


class TestInjectOpencodeConfig:
    def test_creates_new_config(self, tmp_path):
        path = tmp_path / "opencode.jsonc"
        _inject_opencode_config(path, "/usr/bin/agentshare")

        config = json.loads(path.read_text())
        assert config["mcp"]["agentshare"]["type"] == "local"
        assert config["mcp"]["agentshare"]["command"] == ["/usr/bin/agentshare", "mcp", "serve"]
        assert config["mcp"]["agentshare"]["enabled"] is True

    def test_merges_existing(self, tmp_path):
        path = tmp_path / "opencode.jsonc"
        path.write_text(json.dumps({"mcp": {"other": {"type": "local", "command": ["other"]}}}))

        _inject_opencode_config(path, "/usr/bin/agentshare")

        config = json.loads(path.read_text())
        assert "other" in config["mcp"]
        assert "agentshare" in config["mcp"]

    def test_handles_jsonc_comments(self, tmp_path):
        path = tmp_path / "opencode.jsonc"
        path.write_text('{\n  // this is a comment\n  "mcp": {}\n}\n')

        _inject_opencode_config(path, "/usr/bin/agentshare")

        config = json.loads(path.read_text())
        assert "agentshare" in config["mcp"]


class TestRemoveOpencodeConfig:
    def test_removes_entry(self, tmp_path):
        path = tmp_path / "opencode.jsonc"
        _inject_opencode_config(path, "/usr/bin/agentshare")

        _remove_opencode_config(path)

        config = json.loads(path.read_text())
        assert "agentshare" not in config["mcp"]

    def test_noop_if_no_file(self, tmp_path):
        path = tmp_path / "nonexistent.jsonc"
        assert _remove_opencode_config(path) is True
