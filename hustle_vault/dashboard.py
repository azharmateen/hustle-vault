"""Rich dashboard: table of all projects with status, last activity, time spent."""

from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

from hustle_vault.project import get_all_summaries
from hustle_vault.timer import get_all_timers, get_time_report
from hustle_vault.ideas import list_ideas
from hustle_vault.vault import format_duration


def show_dashboard():
    """Display the rich dashboard in the terminal."""
    console = Console()

    summaries = get_all_summaries()
    running_timers = get_all_timers()
    all_ideas = list_ideas()

    # Header
    console.print()
    console.print(Panel.fit(
        "[bold cyan]HUSTLE VAULT[/bold cyan] - Side Project Command Center",
        border_style="cyan"
    ))
    console.print()

    # Stats bar
    active = sum(1 for s in summaries if s["status"] == "active")
    paused = sum(1 for s in summaries if s["status"] == "paused")
    archived = sum(1 for s in summaries if s["status"] == "archived")
    stale = sum(1 for s in summaries if s.get("is_stale") and s["status"] == "active")
    total_ideas = len(all_ideas)

    stats = Columns([
        Panel(f"[bold green]{active}[/] Active", expand=True),
        Panel(f"[bold yellow]{paused}[/] Paused", expand=True),
        Panel(f"[bold dim]{archived}[/] Archived", expand=True),
        Panel(f"[bold red]{stale}[/] Stale", expand=True),
        Panel(f"[bold magenta]{total_ideas}[/] Ideas", expand=True),
    ])
    console.print(stats)
    console.print()

    # Running timers
    if running_timers:
        console.print("[bold yellow]ACTIVE TIMERS[/bold yellow]")
        for t in running_timers:
            console.print(f"  [green]>>>[/green] {t['project']}: {t['elapsed']} (started {t['started_at'][:16]})")
        console.print()

    # Projects table
    if summaries:
        table = Table(title="Projects", border_style="dim", expand=True)
        table.add_column("Name", style="bold", min_width=15)
        table.add_column("Status", justify="center", min_width=8)
        table.add_column("Todos", justify="center")
        table.add_column("Time", justify="right")
        table.add_column("Last Active", justify="right")
        table.add_column("Days Idle", justify="center")
        table.add_column("Path", style="dim", max_width=40)

        for s in summaries:
            # Status coloring
            status_colors = {"active": "green", "paused": "yellow", "archived": "dim"}
            color = status_colors.get(s["status"], "white")
            status_text = Text(s["status"].upper(), style=color)

            # Stale marker
            name_text = s["name"]
            if s.get("is_stale") and s["status"] == "active":
                name_text += " [red]*STALE*[/red]"

            # Todo progress
            todo_text = f"{s['todo_done']}/{s['todo_count']}" if s["todo_count"] > 0 else "-"

            # Days idle
            days = s.get("days_inactive", 0)
            if days > 14:
                days_text = Text(str(days), style="red")
            elif days > 7:
                days_text = Text(str(days), style="yellow")
            else:
                days_text = Text(str(days), style="green")

            # Timer indicator
            time_display = s.get("total_time_display", "0s")
            if s.get("timer_running"):
                time_display = f"[blink]{time_display}[/blink] [green]>>>[/green]"

            # Path (shortened)
            path = s.get("path", "")
            if path:
                home = __import__("os").path.expanduser("~")
                if path.startswith(home):
                    path = "~" + path[len(home):]

            table.add_row(
                name_text,
                status_text,
                todo_text,
                time_display,
                _format_last_active(s),
                days_text,
                path,
            )

        console.print(table)
    else:
        console.print("[dim]No projects yet. Add one with: hustle-vault add <name>[/dim]")

    # Recent ideas
    if all_ideas:
        console.print()
        console.print("[bold magenta]RECENT IDEAS[/bold magenta]")
        for idea in all_ideas[:5]:
            tags = f" [{idea['tags']}]" if idea.get("tags") else ""
            project = f" -> {idea['project_name']}" if idea.get("project_name") else ""
            console.print(f"  [dim]{idea['id']}.[/dim] {idea['text']}{tags}{project}")
        if len(all_ideas) > 5:
            console.print(f"  [dim]... and {len(all_ideas) - 5} more ideas[/dim]")

    console.print()


def _format_last_active(summary: dict) -> str:
    """Format last active timestamp."""
    last = summary.get("last_worked_at") or summary.get("updated_at")
    if not last:
        return "never"
    try:
        dt = datetime.fromisoformat(last)
        days = (datetime.now() - dt).days
        if days == 0:
            return "today"
        elif days == 1:
            return "yesterday"
        elif days < 7:
            return f"{days}d ago"
        elif days < 30:
            return f"{days // 7}w ago"
        else:
            return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return "unknown"
