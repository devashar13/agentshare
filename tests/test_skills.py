"""Tests for skills registry and scaffolding."""

import shutil
from pathlib import Path

import pytest

from agentshare.skills.registry import (
    create_skill,
    get_skill,
    list_skills,
    list_skills_by_category,
    parse_skill,
    remove_skill,
)
from agentshare.skills.scaffold import scaffold_skills


@pytest.fixture
def skills_dir(tmp_path, monkeypatch):
    """Use a temp dir for the skills registry."""
    import agentshare.config as config
    import agentshare.skills.registry as registry

    skills = tmp_path / "skills"
    skills.mkdir()
    monkeypatch.setattr(config, "SKILLS_DIR", skills)
    monkeypatch.setattr(registry, "SKILLS_DIR", skills)
    return skills


@pytest.fixture
def sample_skill(tmp_path):
    """Create a sample skill directory."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: A test skill\ncategory: testing\n---\n# My Skill\nDo stuff.\n"
    )
    return skill_dir


class TestParseSkill:
    def test_parse_valid(self, sample_skill):
        skill = parse_skill(sample_skill)
        assert skill is not None
        assert skill.name == "my-skill"
        assert skill.description == "A test skill"
        assert skill.category == "testing"
        assert "Do stuff." in skill.content

    def test_parse_missing_file(self, tmp_path):
        assert parse_skill(tmp_path) is None

    def test_parse_no_frontmatter(self, tmp_path):
        skill_dir = tmp_path / "plain"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Just content\nNo frontmatter here.")
        skill = parse_skill(skill_dir)
        assert skill is not None
        assert skill.name == "plain"
        assert skill.category == "uncategorized"


class TestRegistry:
    def test_create_and_list(self, skills_dir):
        create_skill("test-skill", "A test", "dev")
        skills = list_skills()
        assert len(skills) == 1
        assert skills[0].name == "test-skill"
        assert skills[0].category == "dev"

    def test_get_skill(self, skills_dir):
        create_skill("findme", "Find this one", "misc")
        skill = get_skill("findme")
        assert skill is not None
        assert skill.name == "findme"

    def test_remove_skill(self, skills_dir):
        create_skill("removeme", "Will be removed")
        assert remove_skill("removeme")
        assert get_skill("removeme") is None
        assert not remove_skill("nonexistent")

    def test_list_by_category(self, skills_dir):
        create_skill("a", category="cat1")
        create_skill("b", category="cat2")
        create_skill("c", category="cat1")
        by_cat = list_skills_by_category()
        assert len(by_cat["cat1"]) == 2
        assert len(by_cat["cat2"]) == 1


class TestScaffold:
    def test_scaffold_to_platforms(self, skills_dir, tmp_path):
        create_skill("my-skill", "Test", "testing")
        project = tmp_path / "myproject"
        project.mkdir()

        results = scaffold_skills(
            project_path=project,
            platforms=["claude", "cursor"],
        )

        assert "my-skill" in results["claude"]
        assert "my-skill" in results["cursor"]
        assert (project / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()
        assert (project / ".cursor" / "skills" / "my-skill" / "SKILL.md").exists()

    def test_scaffold_by_category(self, skills_dir, tmp_path):
        create_skill("a", category="include")
        create_skill("b", category="exclude")
        project = tmp_path / "proj"
        project.mkdir()

        results = scaffold_skills(
            project_path=project,
            platforms=["claude"],
            category="include",
        )

        assert "a" in results["claude"]
        assert "b" not in results["claude"]
