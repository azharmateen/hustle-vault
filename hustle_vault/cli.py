"""Hustle Vault CLI - Side project organizer for developers."""

import click

from hustle_vault.project import add_project, get_project_summary
from hustle_vault.vault import (
    list_projects, update_project, archive_project,
    add_todo, get_todos, toggle_todo, add_note, get_notes, format_duration,
)
from hustle_vault.switcher import switch_project, save_context
from hustle_vault.ideas import add_idea, list_ideas, search_ideas, link_idea_to_project
from hustle_vault.timer import start_timer, stop_timer, get_timer_status, get_time_report
from hustle_vault.dashboard import show_dashboard


@click.group()
@click.version_option(version="1.0.0", prog_name="hustle-vault")
def cli():
    """Hustle Vault - Side project organizer for developers.

    Track multiple projects, capture ideas, time your work, and context-switch efficiently.
    """
    pass


@cli.command()
@click.argument("name")
@click.option("--path", "-p", default="", help="Project directory path")
@click.option("--description", "-d", default="", help="Project description")
def add(name, path, description):
    """Add a new project to the vault."""
    try:
        project = add_project(name, path, description)
        click.echo(f"Project '{name}' added to the vault!")
        click.echo(f"  Path: {project['path']}")
        if project.get("git_branch"):
            click.echo(f"  Branch: {project['git_branch']}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("name")
def switch(name):
    """Switch to a different project."""
    # Find current active project
    projects = list_projects("active")
    current = None
    for p in projects:
        if p.get("last_worked_at"):
            if current is None or p["last_worked_at"] > current["last_worked_at"]:
                current = p

    from_name = current["name"] if current else ""

    try:
        result = switch_project(from_name, name)
        click.echo()
        click.echo(result["welcome_back"])
        click.echo(f"\n  Total time tracked: {result['total_time']}")
        click.echo()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command(name="list")
@click.option("--status", "-s", type=click.Choice(["active", "paused", "archived", "all"]), default="all")
def list_cmd(status):
    """List all projects."""
    status_filter = None if status == "all" else status
    projects = list_projects(status_filter)

    if not projects:
        click.echo("No projects found. Add one with: hustle-vault add <name>")
        return

    click.echo()
    click.echo(f"{'Name':<20} {'Status':<10} {'Last Active':<20} {'Path'}")
    click.echo("-" * 80)

    for p in projects:
        last = p.get("last_worked_at", p.get("updated_at", "never"))
        if last and len(last) > 16:
            last = last[:16]
        path = p.get("path", "")
        click.echo(f"{p['name']:<20} {p['status']:<10} {last:<20} {path}")

    click.echo(f"\nTotal: {len(projects)} projects")


@cli.command()
@click.argument("name")
def status(name):
    """Show detailed status of a project."""
    summary = get_project_summary(name)
    if not summary:
        click.echo(f"Project '{name}' not found.", err=True)
        return

    click.echo()
    click.echo(f"  Project: {summary['name']}")
    click.echo(f"  Status: {summary['status'].upper()}")
    if summary.get("description"):
        click.echo(f"  Description: {summary['description']}")
    click.echo(f"  Path: {summary.get('path', 'not set')}")
    if summary.get("git_branch"):
        click.echo(f"  Branch: {summary['git_branch']}")
    click.echo(f"  Time Tracked: {summary['total_time_display']}")
    if summary["timer_running"]:
        click.echo(f"  Timer: RUNNING")

    # Todos
    todos = get_todos(name)
    if todos:
        done = sum(1 for t in todos if t["done"])
        click.echo(f"\n  Todos ({done}/{len(todos)}):")
        for t in todos:
            marker = "[x]" if t["done"] else "[ ]"
            click.echo(f"    {marker} #{t['id']} {t['text']}")

    # Notes
    notes = get_notes(name)
    if notes:
        click.echo(f"\n  Recent Notes:")
        for n in notes[:5]:
            click.echo(f"    - {n['text'][:60]} ({n['created_at'][:10]})")

    if summary["is_stale"]:
        click.echo(f"\n  WARNING: Stale project ({summary['days_inactive']} days inactive)")

    click.echo()


@cli.command()
@click.argument("text", nargs=-1, required=True)
@click.option("--tags", "-t", default="", help="Comma-separated tags")
@click.option("--project", "-p", default=None, help="Link to a project")
def idea(text, tags, project):
    """Capture a quick idea."""
    text_str = " ".join(text)
    new_idea = add_idea(text_str, tags, project)
    click.echo(f"Idea #{new_idea['id']} saved!")
    if tags:
        click.echo(f"  Tags: {new_idea['tags']}")
    if project:
        click.echo(f"  Linked to: {project}")


@cli.command()
@click.argument("name")
def archive(name):
    """Archive a project."""
    try:
        archive_project(name)
        click.echo(f"Project '{name}' archived.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
def dashboard():
    """Show the rich project dashboard."""
    show_dashboard()


# --- Sub-commands for todos, notes, timer ---

@cli.command()
@click.argument("project")
@click.argument("text", nargs=-1, required=True)
def todo(project, text):
    """Add a todo to a project."""
    text_str = " ".join(text)
    try:
        t = add_todo(project, text_str)
        click.echo(f"Todo #{t['id']} added to {project}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("project")
@click.argument("text", nargs=-1, required=True)
def note(project, text):
    """Add a note to a project."""
    text_str = " ".join(text)
    try:
        n = add_note(project, text_str)
        click.echo(f"Note added to {project}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command(name="timer-start")
@click.argument("project")
def timer_start(project):
    """Start a timer for a project."""
    try:
        result = start_timer(project)
        if result["status"] == "already_running":
            click.echo(f"Timer already running for {project}: {result['elapsed']}")
        else:
            click.echo(f"Timer started for {project}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command(name="timer-stop")
@click.argument("project")
def timer_stop(project):
    """Stop the timer for a project."""
    try:
        result = stop_timer(project)
        if result["status"] == "no_timer":
            click.echo(f"No timer running for {project}")
        else:
            click.echo(f"Timer stopped for {project}: {result['duration']}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command(name="time-report")
def time_report():
    """Show time tracked across all projects."""
    report = get_time_report()
    if not report:
        click.echo("No time tracked yet.")
        return

    click.echo()
    click.echo(f"{'Project':<25} {'Status':<10} {'Time Tracked'}")
    click.echo("-" * 50)
    for r in report:
        click.echo(f"{r['project']:<25} {r['status']:<10} {r['total_display']}")
    click.echo()


@cli.command(name="ideas")
@click.option("--search", "-s", default=None, help="Search ideas")
@click.option("--tag", "-t", default=None, help="Filter by tag")
def ideas_cmd(search, tag):
    """List or search ideas."""
    if search:
        results = search_ideas(search)
    else:
        results = list_ideas(tag=tag)

    if not results:
        click.echo("No ideas found.")
        return

    click.echo()
    for idea in results:
        tags = f" [{idea['tags']}]" if idea.get("tags") else ""
        project = f" -> {idea['project_name']}" if idea.get("project_name") else ""
        click.echo(f"  #{idea['id']} {idea['text']}{tags}{project}")
    click.echo(f"\nTotal: {len(results)} ideas")


if __name__ == "__main__":
    cli()
