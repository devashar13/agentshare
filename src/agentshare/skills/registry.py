"""Skills registry - load, list, and manage skills from ~/.agentshare/skills/."""

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from agentshare.config import SKILLS_DIR, ensure_dirs


@dataclass
class Skill:
    """A parsed skill with its metadata and content."""

    name: str
    description: str
    category: str
    path: Path
    content: str
    raw: str = ""

    @property
    def display_name(self) -> str:
        return self.name.replace("-", " ").title()


SKILL_TEMPLATE = """---
name: {name}
description: {description}
category: {category}
---

# {title}

[Add your skill instructions here]
"""


def parse_skill(path: Path) -> Skill | None:
    """Parse a SKILL.md file into a Skill object."""
    skill_file = path / "SKILL.md"
    if not skill_file.exists():
        return None

    raw = skill_file.read_text()

    # Parse YAML frontmatter
    name = path.name
    description = ""
    category = "uncategorized"
    content = raw

    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            content = parts[2].strip()
            for line in frontmatter.splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip()
                    if key == "name":
                        name = value
                    elif key == "description":
                        description = value
                    elif key == "category":
                        category = value

    return Skill(
        name=name,
        description=description,
        category=category,
        path=path,
        content=content,
        raw=raw,
    )


def list_skills() -> list[Skill]:
    """List all skills from the registry."""
    ensure_dirs()
    skills = []

    # Walk through category dirs and skill dirs
    for item in sorted(SKILLS_DIR.iterdir()):
        if item.is_dir():
            # Could be a category dir or a direct skill dir
            skill = parse_skill(item)
            if skill:
                skills.append(skill)
            else:
                # Category directory - look for skills inside
                for sub in sorted(item.iterdir()):
                    if sub.is_dir():
                        skill = parse_skill(sub)
                        if skill:
                            skill.category = item.name
                            skills.append(skill)

    return skills


def list_skills_by_category() -> dict[str, list[Skill]]:
    """List skills grouped by category."""
    skills = list_skills()
    by_category: dict[str, list[Skill]] = {}
    for skill in skills:
        by_category.setdefault(skill.category, []).append(skill)
    return by_category


def add_skill(source: Path) -> Skill:
    """Import a skill directory into the registry."""
    ensure_dirs()
    skill = parse_skill(source)
    if not skill:
        raise ValueError(f"No SKILL.md found in {source}")

    dest = SKILLS_DIR / skill.category / skill.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)

    return parse_skill(dest)  # type: ignore[return-value]


def remove_skill(name: str) -> bool:
    """Remove a skill from the registry by name."""
    for skill in list_skills():
        if skill.name == name:
            shutil.rmtree(skill.path)
            return True
    return False


def create_skill(
    name: str, description: str = "", category: str = "uncategorized"
) -> Skill:
    """Create a new empty skill in the registry."""
    ensure_dirs()
    dest = SKILLS_DIR / category / name
    dest.mkdir(parents=True, exist_ok=True)

    title = name.replace("-", " ").title()
    content = SKILL_TEMPLATE.format(
        name=name, description=description, category=category, title=title
    )
    (dest / "SKILL.md").write_text(content)

    return parse_skill(dest)  # type: ignore[return-value]


def get_skill(name: str) -> Skill | None:
    """Get a skill by name."""
    for skill in list_skills():
        if skill.name == name:
            return skill
    return None
