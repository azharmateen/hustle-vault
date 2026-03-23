"""Context switcher: save and restore project state when switching."""

import json
import os
import subprocess
from datetime import datetime
from typing import Optional

from hustle_vault.vault import get_db, get_project, update_project, format_duration, get_total_time


def save_context(project_name: str, open_files: list = None, notes: str = "") -> dict:
    """Save current context for a project."""
    project = get_project(project_name)
    if not project:
        raise ValueError(f"Project '{project_name}' not found")

    # Detect current git branch
    git_branch = ""
    if project["path"] and os.path.isdir(os.path.join(project["path"], ".git")):
        try:
            result = subprocess.run(
                ["git", "-C", project["path"], "branch", "--show-current"],
                capture_output=True, text=True, timeout=5
            )
            git_branch = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    conn = get_db()
    now = datetime.now().isoformat()

    # Upsert context state
    existing = conn.execute(
        "SELECT id FROM context_state WHERE project_id = ?", (project["id"],)
    ).fetchone()

    files_json = json.dumps(open_files or [])

    if existing:
        conn.execute(
            "UPDATE context_state SET open_files = ?, git_branch = ?, notes = ?, saved_at = ? WHERE project_id = ?",
            (files_json, git_branch, notes, now, project["id"])
        )
    else:
        conn.execute(
            "INSERT INTO context_state (project_id, open_files, git_branch, notes, saved_at) VALUES (?, ?, ?, ?, ?)",
            (project["id"], files_json, git_branch, notes, now)
        )

    conn.commit()
    conn.close()

    # Update git branch on project
    if git_branch:
        update_project(project_name, git_branch=git_branch)

    return {"project": project_name, "git_branch": git_branch, "saved_at": now}


def restore_context(project_name: str) -> Optional[dict]:
    """Restore saved context for a project."""
    project = get_project(project_name)
    if not project:
        return None

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM context_state WHERE project_id = ? ORDER BY saved_at DESC LIMIT 1",
        (project["id"],)
    ).fetchone()
    conn.close()

    if not row:
        return {
            "project": project_name,
            "path": project["path"],
            "open_files": [],
            "git_branch": project.get("git_branch", ""),
            "notes": "",
            "has_saved_state": False,
        }

    context = dict(row)
    try:
        context["open_files"] = json.loads(context.get("open_files", "[]"))
    except (json.JSONDecodeError, TypeError):
        context["open_files"] = []

    return {
        "project": project_name,
        "path": project["path"],
        "open_files": context["open_files"],
        "git_branch": context.get("git_branch", ""),
        "notes": context.get("notes", ""),
        "has_saved_state": True,
        "saved_at": context.get("saved_at"),
    }


def switch_project(from_name: str, to_name: str) -> dict:
    """Switch from one project to another, saving and restoring context."""
    from_project = get_project(from_name)
    to_project = get_project(to_name)

    if not to_project:
        raise ValueError(f"Project '{to_name}' not found")

    # Save current context
    saved = None
    if from_project:
        saved = save_context(from_name)

    # Restore target context
    restored = restore_context(to_name)

    # Mark target as last worked
    now = datetime.now().isoformat()
    update_project(to_name, last_worked_at=now, status="active")

    # Calculate time since last work
    total_time = get_total_time(to_name)

    return {
        "from_project": from_name,
        "to_project": to_name,
        "saved_context": saved,
        "restored_context": restored,
        "total_time": format_duration(total_time),
        "welcome_back": _welcome_back_message(to_project, restored),
    }


def _welcome_back_message(project: dict, context: Optional[dict]) -> str:
    """Generate a welcome back message with last activity summary."""
    lines = []
    lines.append(f"Welcome back to {project['name']}!")

    if project.get("description"):
        lines.append(f"  {project['description']}")

    if project.get("path"):
        lines.append(f"  Path: {project['path']}")

    if context and context.get("git_branch"):
        lines.append(f"  Branch: {context['git_branch']}")

    last = project.get("last_worked_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            days = (datetime.now() - last_dt).days
            if days == 0:
                lines.append("  Last active: today")
            elif days == 1:
                lines.append("  Last active: yesterday")
            else:
                lines.append(f"  Last active: {days} days ago")
        except (ValueError, TypeError):
            pass

    if context and context.get("notes"):
        lines.append(f"  Notes: {context['notes']}")

    if context and context.get("open_files"):
        lines.append(f"  Previously open files:")
        for f in context["open_files"][:5]:
            lines.append(f"    - {f}")
        if len(context["open_files"]) > 5:
            lines.append(f"    ... and {len(context['open_files']) - 5} more")

    return "\n".join(lines)
