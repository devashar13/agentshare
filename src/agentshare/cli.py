"""AgentShare CLI - unifying layer for AI coding agents."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from agentshare import __version__
from agentshare.config import detect_platforms, ensure_dirs

app = typer.Typer(
    name="agentshare",
    help="Share skills and context across AI coding agents.",
    no_args_is_help=True,
)
skills_app = typer.Typer(help="Manage the skills registry.")
mcp_app = typer.Typer(help="MCP server management.")
init_app = typer.Typer(help="Initialize features in a project.")

app.add_typer(skills_app, name="skills")
app.add_typer(mcp_app, name="mcp")
app.add_typer(init_app, name="init")

console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"agentshare {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """AgentShare - share skills and context across AI coding agents."""
    ensure_dirs()


# ── Skills commands ──────────────────────────────────────────────


@skills_app.command("list")
def skills_list() -> None:
    """List all skills in the registry by category."""
    from agentshare.skills.registry import list_skills_by_category

    by_category = list_skills_by_category()
    if not by_category:
        console.print("[dim]No skills in registry. Add some with:[/dim]")
        console.print("  agentshare skills create <name>")
        console.print("  agentshare skills add <path>")
        return

    table = Table(title="Skills Registry")
    table.add_column("Category", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description")

    for category, skills in sorted(by_category.items()):
        for skill in skills:
            table.add_row(category, skill.name, skill.description)

    console.print(table)


@skills_app.command("add")
def skills_add(
    path: Annotated[Path, typer.Argument(help="Path to skill directory to import")],
) -> None:
    """Import a skill directory into the registry."""
    from agentshare.skills.registry import add_skill

    path = path.resolve()
    if not path.is_dir():
        console.print(f"[red]Error:[/red] {path} is not a directory")
        raise typer.Exit(1)

    skill = add_skill(path)
    console.print(f"[green]Added skill:[/green] {skill.name} ({skill.category})")


@skills_app.command("remove")
def skills_remove(
    name: Annotated[str, typer.Argument(help="Skill name to remove")],
) -> None:
    """Remove a skill from the registry."""
    from agentshare.skills.registry import remove_skill

    if remove_skill(name):
        console.print(f"[green]Removed skill:[/green] {name}")
    else:
        console.print(f"[red]Skill not found:[/red] {name}")
        raise typer.Exit(1)


@skills_app.command("create")
def skills_create(
    name: Annotated[str, typer.Argument(help="Name for the new skill")],
    description: Annotated[str, typer.Option("--description", "-d", help="Skill description")] = "",
    category: Annotated[str, typer.Option("--category", "-c", help="Skill category")] = "uncategorized",
) -> None:
    """Create a new empty skill in the registry."""
    from agentshare.skills.registry import create_skill

    skill = create_skill(name, description, category)
    console.print(f"[green]Created skill:[/green] {skill.name}")
    console.print(f"  Edit: {skill.path / 'SKILL.md'}")


# ── Init commands ────────────────────────────────────────────────


@init_app.command("skills")
def init_skills(
    project_path: Annotated[
        Path, typer.Option("--path", "-p", help="Project path")
    ] = Path("."),
    platform: Annotated[
        Optional[str],
        typer.Option("--platform", help="Target platform (claude, cursor, windsurf)"),
    ] = None,
    all_platforms: Annotated[
        bool, typer.Option("--all-platforms", help="Scaffold for all platforms")
    ] = False,
    category: Annotated[
        Optional[str], typer.Option("--category", "-c", help="Only skills from category")
    ] = None,
    all_skills: Annotated[
        bool, typer.Option("--all", help="Scaffold all skills")
    ] = True,
) -> None:
    """Scaffold skills into platform-specific directories."""
    from agentshare.skills.scaffold import scaffold_skills

    project_path = project_path.resolve()

    platforms = None
    if platform:
        platforms = [platform]
    elif all_platforms:
        platforms = ["claude", "cursor", "windsurf"]

    results = scaffold_skills(
        project_path=project_path,
        platforms=platforms,
        category=category,
    )

    if not any(results.values()):
        console.print("[yellow]No skills to scaffold.[/yellow]")
        console.print("Add skills first: agentshare skills create <name>")
        return

    for plat, skill_names in results.items():
        if skill_names:
            console.print(f"[green]{plat}:[/green] {', '.join(skill_names)}")


# ── MCP commands ─────────────────────────────────────────────────


@mcp_app.command("serve")
def mcp_serve() -> None:
    """Start the MCP server (stdio transport)."""
    from agentshare.mcp.server import mcp

    mcp.run()


@mcp_app.command("init")
def mcp_init(
    global_install: Annotated[
        bool, typer.Option("--global", "-g", help="Install globally for all detected platforms")
    ] = False,
    project_path: Annotated[
        Path, typer.Option("--path", "-p", help="Project path for local install")
    ] = Path("."),
) -> None:
    """Configure the MCP server in AI coding platforms."""
    from agentshare.mcp.installer import install_mcp_global, install_mcp_project

    if global_install:
        detected = detect_platforms()
        if not detected:
            console.print("[yellow]No supported platforms detected.[/yellow]")
            console.print("Looked for: Claude Code, Cursor, Windsurf, Codex, OpenCode")
            raise typer.Exit(1)

        console.print(f"Detected platforms: {', '.join(detected)}")
        results = install_mcp_global()
        mcp_results = results["mcp"]
        rules_results = results["rules"]
        skills_results = results["skills"]

        console.print("\n[bold]MCP server config:[/bold]")
        for platform, success in mcp_results.items():
            icon = "[green]✓[/green]" if success else "[red]✗[/red]"
            console.print(f"  {icon} {platform}")

        console.print("\n[bold]Agent rules:[/bold]")
        for platform, success in rules_results.items():
            icon = "[green]✓[/green]" if success else "[red]✗[/red]"
            console.print(f"  {icon} {platform}")

        console.print("\n[bold]Skills:[/bold]")
        for platform, success in skills_results.items():
            icon = "[green]✓[/green]" if success else "[red]✗[/red]"
            console.print(f"  {icon} {platform}")

        # Note OpenCode if detected but skipped
        if "opencode" in detected and "opencode" not in mcp_results:
            console.print("\n[dim]OpenCode detected but uses project-scoped config only.[/dim]")
            console.print("[dim]Run: agentshare mcp init --path /your/project[/dim]")

        if any(mcp_results.values()):
            console.print("\n[dim]Restart your AI agents to pick up the new MCP server.[/dim]")
    else:
        project_path = project_path.resolve()
        results = install_mcp_project(project_path)

        for name, success in results.items():
            icon = "[green]✓[/green]" if success else "[red]✗[/red]"
            console.print(f"  {icon} {project_path / name}")

        if not any(results.values()):
            console.print("[red]Failed to write MCP config.[/red]")
            raise typer.Exit(1)


@mcp_app.command("remove")
def mcp_remove() -> None:
    """Remove AgentShare MCP config and agent rules from all platforms."""
    from agentshare.mcp.installer import remove_mcp_global

    detected = detect_platforms()
    if not detected:
        console.print("[yellow]No supported platforms detected.[/yellow]")
        raise typer.Exit(1)

    results = remove_mcp_global()
    mcp_results = results["mcp"]
    rules_results = results["rules"]
    skills_results = results["skills"]

    console.print("[bold]MCP server config:[/bold]")
    for platform, success in mcp_results.items():
        icon = "[green]✓[/green]" if success else "[red]✗[/red]"
        console.print(f"  {icon} {platform}")

    console.print("\n[bold]Agent rules:[/bold]")
    for platform, success in rules_results.items():
        icon = "[green]✓[/green]" if success else "[red]✗[/red]"
        console.print(f"  {icon} {platform}")

    console.print("\n[bold]Skills:[/bold]")
    for platform, success in skills_results.items():
        icon = "[green]✓[/green]" if success else "[red]✗[/red]"
        console.print(f"  {icon} {platform}")

    if any(mcp_results.values()) or any(rules_results.values()) or any(skills_results.values()):
        console.print("\n[dim]Restart your AI agents to complete removal.[/dim]")
