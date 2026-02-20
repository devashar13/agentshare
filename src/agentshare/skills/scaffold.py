"""Scaffold skills into platform-specific directories."""

import shutil
from pathlib import Path

from agentshare.config import PLATFORM_SKILL_DIRS, detect_platforms
from agentshare.skills.registry import Skill, list_skills, list_skills_by_category


def scaffold_skill(skill: Skill, platform: str, project_path: Path) -> Path:
    """Copy a skill to a platform-specific directory in a project."""
    rel_dir = PLATFORM_SKILL_DIRS[platform]
    dest = project_path / rel_dir / skill.name
    dest.mkdir(parents=True, exist_ok=True)

    # Copy all files from the skill directory
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(skill.path, dest)

    return dest


def scaffold_skills(
    project_path: Path,
    platforms: list[str] | None = None,
    category: str | None = None,
    skill_names: list[str] | None = None,
) -> dict[str, list[str]]:
    """Scaffold skills into platform dirs. Returns {platform: [skill_names]}."""
    if platforms is None:
        platforms = [p for p in detect_platforms() if p in PLATFORM_SKILL_DIRS]
        if not platforms:
            platforms = list(PLATFORM_SKILL_DIRS.keys())
    else:
        platforms = [p for p in platforms if p in PLATFORM_SKILL_DIRS]

    # Determine which skills to scaffold
    if skill_names:
        all_skills = list_skills()
        skills = [s for s in all_skills if s.name in skill_names]
    elif category:
        by_cat = list_skills_by_category()
        skills = by_cat.get(category, [])
    else:
        skills = list_skills()

    results: dict[str, list[str]] = {}
    for platform in platforms:
        results[platform] = []
        for skill in skills:
            scaffold_skill(skill, platform, project_path)
            results[platform].append(skill.name)

    return results
