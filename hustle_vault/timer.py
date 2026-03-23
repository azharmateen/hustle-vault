"""Time tracker: start/stop timer per project, track sessions, report totals."""

from datetime import datetime
from typing import Optional

from hustle_vault.vault import get_db, get_project, update_project, format_duration


def start_timer(project_name: str) -> dict:
    """Start a timer for a project."""
    project = get_project(project_name)
    if not project:
        raise ValueError(f"Project '{project_name}' not found")

    conn = get_db()

    # Check for already-running timer
    running = conn.execute(
        "SELECT * FROM time_entries WHERE project_id = ? AND ended_at IS NULL",
        (project["id"],)
    ).fetchone()

    if running:
        conn.close()
        started = datetime.fromisoformat(running["started_at"])
        elapsed = (datetime.now() - started).total_seconds()
        return {
            "status": "already_running",
            "project": project_name,
            "started_at": running["started_at"],
            "elapsed": format_duration(int(elapsed)),
        }

    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO time_entries (project_id, started_at) VALUES (?, ?)",
        (project["id"], now)
    )
    conn.commit()
    conn.close()

    # Update last worked
    update_project(project_name, last_worked_at=now, status="active")

    return {
        "status": "started",
        "project": project_name,
        "started_at": now,
    }


def stop_timer(project_name: str) -> dict:
    """Stop the running timer for a project."""
    project = get_project(project_name)
    if not project:
        raise ValueError(f"Project '{project_name}' not found")

    conn = get_db()
    running = conn.execute(
        "SELECT * FROM time_entries WHERE project_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
        (project["id"],)
    ).fetchone()

    if not running:
        conn.close()
        return {"status": "no_timer", "project": project_name}

    now = datetime.now()
    started = datetime.fromisoformat(running["started_at"])
    duration = int((now - started).total_seconds())

    conn.execute(
        "UPDATE time_entries SET ended_at = ?, duration_seconds = ? WHERE id = ?",
        (now.isoformat(), duration, running["id"])
    )
    conn.commit()
    conn.close()

    update_project(project_name, last_worked_at=now.isoformat())

    return {
        "status": "stopped",
        "project": project_name,
        "duration": format_duration(duration),
        "duration_seconds": duration,
        "started_at": running["started_at"],
        "ended_at": now.isoformat(),
    }


def get_timer_status(project_name: str) -> dict:
    """Get current timer status for a project."""
    project = get_project(project_name)
    if not project:
        raise ValueError(f"Project '{project_name}' not found")

    conn = get_db()
    running = conn.execute(
        "SELECT * FROM time_entries WHERE project_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
        (project["id"],)
    ).fetchone()

    if running:
        started = datetime.fromisoformat(running["started_at"])
        elapsed = int((datetime.now() - started).total_seconds())
        conn.close()
        return {
            "running": True,
            "project": project_name,
            "started_at": running["started_at"],
            "elapsed": format_duration(elapsed),
            "elapsed_seconds": elapsed,
        }

    conn.close()
    return {"running": False, "project": project_name}


def get_sessions(project_name: str, limit: int = 20) -> list:
    """Get recent time sessions for a project."""
    project = get_project(project_name)
    if not project:
        return []

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM time_entries WHERE project_id = ? AND ended_at IS NOT NULL "
        "ORDER BY started_at DESC LIMIT ?",
        (project["id"], limit)
    ).fetchall()
    conn.close()

    return [
        {
            **dict(r),
            "duration_display": format_duration(r["duration_seconds"]),
        }
        for r in rows
    ]


def get_all_timers() -> list:
    """Get all currently running timers across all projects."""
    conn = get_db()
    rows = conn.execute(
        "SELECT te.*, p.name as project_name FROM time_entries te "
        "JOIN projects p ON te.project_id = p.id "
        "WHERE te.ended_at IS NULL ORDER BY te.started_at DESC"
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        started = datetime.fromisoformat(r["started_at"])
        elapsed = int((datetime.now() - started).total_seconds())
        result.append({
            "project": r["project_name"],
            "started_at": r["started_at"],
            "elapsed": format_duration(elapsed),
            "elapsed_seconds": elapsed,
        })
    return result


def get_time_report() -> list:
    """Get total time per project."""
    conn = get_db()
    rows = conn.execute(
        "SELECT p.name, p.status, COALESCE(SUM(te.duration_seconds), 0) as total_seconds "
        "FROM projects p LEFT JOIN time_entries te ON p.id = te.project_id AND te.ended_at IS NOT NULL "
        "GROUP BY p.id ORDER BY total_seconds DESC"
    ).fetchall()
    conn.close()

    return [
        {
            "project": r["name"],
            "status": r["status"],
            "total_seconds": r["total_seconds"],
            "total_display": format_duration(r["total_seconds"]),
        }
        for r in rows
    ]
