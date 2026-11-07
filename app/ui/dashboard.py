
from datetime import datetime
from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


console = Console()

STAGES = [
    ("ready", "Ready"),
    ("waiting_for_user", "Waiting for User"),
    ("ticket_selection", "Ticket Selection"),
    ("checkout", "Checkout"),
]


def format_elapsed(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_release_info(release_at: str) -> tuple[str, str]:
    try:
        release_time = datetime.fromisoformat(release_at)
        if release_time.tzinfo is None:
            return "Invalid release timezone", "Unknown"

        local_release = release_time.astimezone()
        now = datetime.now().astimezone()
        remaining = (local_release - now).total_seconds()

        release_label = local_release.strftime("%Y-%m-%d %I:%M:%S %p %Z")

        if remaining <= 0:
            return release_label, "Release time reached"

        return release_label, format_elapsed(remaining)

    except (ValueError, TypeError):
        return "Invalid release date", "Unknown"


def display_dashboard(
    current_stage: str = "Not started",
    elapsed_seconds: float = 0.0,
    status: str = "Ready",
    event_name: str = "Rashed Al Majid Concert",
    event_url: str = "",
    release_at: str = "2026-11-07T17:00:00+03:00",
):
    console.clear()

    header = Text()
    header.append("WEBOOK ", style="bold cyan")
    header.append("BOOKING ASSISTANT", style="bold white")
    header.append("\nManual Session Management", style="dim")

    console.print(
        Panel(
            Align.center(header, vertical="middle"),
            border_style="cyan",
            padding=(1, 2),
        )
    )

    release_label, countdown = get_release_info(release_at)

    event_table = Table(
        title="EVENT INFORMATION",
        box=box.ROUNDED,
        expand=True,
        border_style="magenta",
    )
    event_table.add_column("Detail", style="cyan")
    event_table.add_column("Value", style="white")

    event_table.add_row("Event", event_name)
    event_table.add_row("Date / time", "Check the official event page")
    event_table.add_row("Venue", "Check the official event page")
    event_table.add_row("Configured release", release_label)
    event_table.add_row("Time Remaining", f"[bold yellow]{countdown}[/]")
    event_table.add_row("Official Event Page", event_url or "Not configured")

    console.print(event_table)

    ticket_table = Table(
        title="TICKET CATEGORY POLICY",
        box=box.ROUNDED,
        expand=True,
        border_style="magenta",
    )
    ticket_table.add_column("Category", style="cyan")
    ticket_table.add_column("Client rule", justify="right", style="white")
    ticket_table.add_row("Bronze", "Preferred")
    ticket_table.add_row("Silver", "Fallback · approval required")
    ticket_table.add_row("Quantity", "User-selected: 1–3 tickets")
    ticket_table.add_row("Prices / other categories", "Read from the live event page (option 7)")
    console.print(ticket_table)

    status_style = (
        "bold green"
        if status.lower() == "tracking"
        else "bold yellow"
        if status.lower() == "safety stop"
        else "bold cyan"
    )

    overview = Table(
        title="SESSION OVERVIEW",
        box=box.ROUNDED,
        expand=True,
        border_style="blue",
    )
    overview.add_column("Metric", style="cyan")
    overview.add_column("Value", style="white")

    overview.add_row("Session Status", f"[{status_style}]{status}[/]")
    overview.add_row("Current Stage", current_stage.replace("_", " ").title())
    overview.add_row("Elapsed Time", f"[bold]{format_elapsed(elapsed_seconds)}[/]")

    console.print(overview)

    stage_table = Table(
        title="BOOKING STAGES",
        box=box.ROUNDED,
        expand=True,
        border_style="blue",
    )
    stage_table.add_column("Stage", style="white")
    stage_table.add_column("State", justify="right")

    for stage_key, stage_label in STAGES:
        if current_stage == stage_key:
            stage_table.add_row(stage_label, "[bold green]● CURRENT[/]")
        else:
            stage_table.add_row(stage_label, "[dim]○ NOT ACTIVE[/]")

    console.print(stage_table)

    preferences = Table(
        title="TICKET PREFERENCES",
        box=box.ROUNDED,
        expand=True,
        border_style="blue",
    )
    preferences.add_column("Setting", style="cyan")
    preferences.add_column("Configured Value", style="white")

    preferences.add_row("Quantity", "Selected per session (1–3)")
    preferences.add_row("Preferred Category", "[green]Bronze[/]")
    preferences.add_row("Fallback Category", "[yellow]Silver - approval required[/]")
    preferences.add_row("Area / adjacency", "Selected per session")
    preferences.add_row("Payment", "[bold red]Manual only[/]")

    console.print(preferences)

    safety_message = (
        "[green]Manual session tracking enabled[/]\n"
        "[yellow]Visible persistent browser; sign-in is manual[/]\n"
        "[yellow]No queue bypass or automated seat selection[/]\n"
        "[red]Checkout is a handoff. Payment remains manual.[/]"
    )

    console.print(
        Panel(
            safety_message,
            title="[bold]SAFETY CONTROLS[/]",
            border_style="green",
            padding=(1, 2),
        )
    )

    console.print(
        Align.center(
            "[dim]Use the numbered menu below to update the session stage.[/]"
        )
    )
