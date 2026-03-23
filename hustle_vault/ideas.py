"""Idea bank: quick capture ideas with tags, link to projects, search."""

from datetime import datetime
from typing import Optional

from hustle_vault.vault import get_db, get_project


def add_idea(text: str, tags: str = "", project_name: str = None) -> dict:
    """Add a new idea to the vault."""
    conn = get_db()
    now = datetime.now().isoformat()

    project_id = None
    if project_name:
        project = get_project(project_name)
        if project:
            project_id = project["id"]

    # Normalize tags: comma-separated, lowercased, stripped
    if tags:
        tags = ",".join(t.strip().lower() for t in tags.split(",") if t.strip())

    cursor = conn.execute(
        "INSERT INTO ideas (text, tags, project_id, created_at) VALUES (?, ?, ?, ?)",
        (text, tags, project_id, now)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM ideas WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def list_ideas(project_name: str = None, tag: str = None) -> list:
    """List all ideas, optionally filtered by project or tag."""
    conn = get_db()

    query = "SELECT i.*, p.name as project_name FROM ideas i LEFT JOIN projects p ON i.project_id = p.id"
    params = []
    conditions = []

    if project_name:
        project = get_project(project_name)
        if project:
            conditions.append("i.project_id = ?")
            params.append(project["id"])

    if tag:
        conditions.append("i.tags LIKE ?")
        params.append(f"%{tag.lower()}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY i.created_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_ideas(query: str) -> list:
    """Search ideas by text content."""
    conn = get_db()
    rows = conn.execute(
        "SELECT i.*, p.name as project_name FROM ideas i LEFT JOIN projects p ON i.project_id = p.id "
        "WHERE i.text LIKE ? OR i.tags LIKE ? ORDER BY i.created_at DESC",
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def link_idea_to_project(idea_id: int, project_name: str) -> Optional[dict]:
    """Link an idea to a project."""
    project = get_project(project_name)
    if not project:
        raise ValueError(f"Project '{project_name}' not found")

    conn = get_db()
    conn.execute("UPDATE ideas SET project_id = ? WHERE id = ?", (project["id"], idea_id))
    conn.commit()
    row = conn.execute(
        "SELECT i.*, p.name as project_name FROM ideas i LEFT JOIN projects p ON i.project_id = p.id WHERE i.id = ?",
        (idea_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_idea(idea_id: int) -> bool:
    """Delete an idea."""
    conn = get_db()
    cursor = conn.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
