"""Vault storage: SQLite database in ~/.hustle-vault/ for projects, ideas, time entries."""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_DIR = os.path.join(str(Path.home()), ".hustle-vault")
DB_PATH = os.path.join(DB_DIR, "vault.db")


def get_db() -> sqlite3.Connection:
    """Get database connection, creating schema if needed."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection):
    """Create all tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            path TEXT,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'archived')),
            git_branch TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_worked_at TEXT
        );

        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            tags TEXT DEFAULT '',
            project_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES ideas(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            duration_seconds INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS context_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            open_files TEXT DEFAULT '[]',
            git_branch TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            saved_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
    """)
    conn.commit()


# --- Project CRUD ---

def create_project(name: str, path: str = "", description: str = "") -> dict:
    """Create a new project."""
    now = datetime.now().isoformat()
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO projects (name, path, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (name, path, description, now, now)
        )
        conn.commit()
        return get_project(name)
    except sqlite3.IntegrityError:
        raise ValueError(f"Project '{name}' already exists")
    finally:
        conn.close()


def get_project(name: str) -> Optional[dict]:
    """Get project by name."""
    conn = get_db()
    row = conn.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_project_by_id(project_id: int) -> Optional[dict]:
    """Get project by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_projects(status: str = None) -> list:
    """List all projects, optionally filtered by status."""
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_project(name: str, **kwargs) -> dict:
    """Update project fields."""
    conn = get_db()
    allowed = {"path", "description", "status", "git_branch", "last_worked_at"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    updates["updated_at"] = datetime.now().isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [name]
    conn.execute(f"UPDATE projects SET {set_clause} WHERE name = ?", values)
    conn.commit()
    result = get_project(name)
    conn.close()
    return result


def archive_project(name: str) -> dict:
    """Archive a project."""
    return update_project(name, status="archived")


# --- Todos ---

def add_todo(project_name: str, text: str) -> dict:
    """Add a todo to a project."""
    project = get_project(project_name)
    if not project:
        raise ValueError(f"Project '{project_name}' not found")
    conn = get_db()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        "INSERT INTO todos (project_id, text, created_at) VALUES (?, ?, ?)",
        (project["id"], text, now)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def get_todos(project_name: str) -> list:
    """Get all todos for a project."""
    project = get_project(project_name)
    if not project:
        return []
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM todos WHERE project_id = ? ORDER BY created_at", (project["id"],)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_todo(todo_id: int) -> dict:
    """Toggle a todo's done status."""
    conn = get_db()
    conn.execute("UPDATE todos SET done = NOT done WHERE id = ?", (todo_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Notes ---

def add_note(project_name: str, text: str) -> dict:
    """Add a note to a project."""
    project = get_project(project_name)
    if not project:
        raise ValueError(f"Project '{project_name}' not found")
    conn = get_db()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        "INSERT INTO notes (project_id, text, created_at) VALUES (?, ?, ?)",
        (project["id"], text, now)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def get_notes(project_name: str) -> list:
    """Get all notes for a project."""
    project = get_project(project_name)
    if not project:
        return []
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notes WHERE project_id = ? ORDER BY created_at DESC", (project["id"],)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Time Entries ---

def get_total_time(project_name: str) -> int:
    """Get total time spent on a project in seconds."""
    project = get_project(project_name)
    if not project:
        return 0
    conn = get_db()
    row = conn.execute(
        "SELECT COALESCE(SUM(duration_seconds), 0) as total FROM time_entries WHERE project_id = ?",
        (project["id"],)
    ).fetchone()
    conn.close()
    return row["total"] if row else 0


def get_active_timer(project_name: str) -> Optional[dict]:
    """Get currently running timer for a project."""
    project = get_project(project_name)
    if not project:
        return None
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM time_entries WHERE project_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
        (project["id"],)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
