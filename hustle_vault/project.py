"""Project model and high-level operations."""

import os
import subprocess
from datetime import datetime
from typing import Optional

from hustle_vault.vault import (
    create_project, get_project, list_projects, update_project,
    archive_project, get_total_time, get_active_timer, format_duration,
    get_todos, get_notes,
)


def add_project(name: str, path: str = "", description: str = "") -> dict:
    """Add a new project to the vault."""
    if not path:
        path = os.getcwd()
    path = os.path.abspath(path)

    # Detect git branch if in a git repo
    git_branch = ""
    if os.path.isdir(os.path.join(path, ".git")):
        try:
            result = subprocess.run(
                ["git", "-C", path, "branch", "--show-current"],
                capture_output=True, text=True, timeout=5
            )
            git_branch = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    project = create_project(name, path, description)
    if git_branch:
        project = update_project(name, git_branch=git_branch)

    return project


def get_project_summary(name: str) -> Optional[dict]:
    """Get a project with enriched summary data."""
    project = get_project(name)
    if not project:
        return None

    total_time = get_total_time(name)
    active_timer = get_active_timer(name)
    todos = get_todos(name)
    notes = get_notes(name)

    return {
        **project,
        "total_time_seconds": total_time,
        "total_time_display": format_duration(total_time),
        "timer_running": active_timer is not None,
        "todo_count": len(todos),
        "todo_done": sum(1 for t in todos if t["done"]),
        "note_count": len(notes),
        "is_stale": _is_stale(project),
        "days_inactive": _days_inactive(project),
    }


def get_all_summaries(status: str = None) -> list:
    """Get summaries for all projects."""
    projects = list_projects(status)
    return [get_project_summary(p["name"]) for p in projects]


def _is_stale(project: dict) -> bool:
    """Check if project hasn't been worked on in 14+ days."""
    last = project.get("last_worked_at") or project.get("updated_at")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
        return (datetime.now() - last_dt).days > 14
    except (ValueError, TypeError):
        return False


def _days_inactive(project: dict) -> int:
    """Calculate days since last activity."""
    last = project.get("last_worked_at") or project.get("updated_at")
    if not last:
        return 0
    try:
        last_dt = datetime.fromisoformat(last)
        return (datetime.now() - last_dt).days
    except (ValueError, TypeError):
        return 0
