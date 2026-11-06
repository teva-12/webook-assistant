from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()


def display_dashboard(
    current_stage: str = "Not started",
    elapsed_seconds: float = 0.0,
    status: str = "Ready",
):
    console.clear()

    header = """
 __        __ ____  ____   ___   ___  _  __
 \\ \\      / /| __ )|  _ \\ / _ \\ / _ \\| |/ /
  \\ \\ /\\ / / |  _ \\| |_) | | | | | | | ' /
   \\ V  V /  | |_) |  _ <| |_| | |_| | . \\
    \\_/\\_/   |____/|_| \\_\\\\___/ \\___/|_|\\_\\
    """

    console.print(
        Panel(
            Align.center(header, vertical="middle"),
            title="[bold cyan]BOOKING ASSISTANT[/bold cyan]",
            border_style="cyan",
        )
    )

    table = Table(
        title="Session Overview",
        box=box.ROUNDED,
        expand=True,
    )

    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Status", status)
    table.add_row("Current Stage", current_stage)
    table.add_row("Elapsed Time", f"{elapsed_seconds:.2f} seconds")

    console.print(table)

    preferences = Table(
        title="Ticket Preferences",
        box=box.ROUNDED,
        expand=True,
    )

    preferences.add_column("Setting", style="cyan")
    preferences.add_column("Preference", style="white")

    preferences.add_row("Quantity", "2 tickets")
    preferences.add_row("First Choice", "[green]Bronze[/green]")
    preferences.add_row("Fallback", "[yellow]Silver (approval required)[/yellow]")
    preferences.add_row("Payment", "[bold red]Manual only[/bold red]")

    console.print(preferences)

    console.print(
        Panel(
            "[green]Manual session tracking enabled[/green]\n"
            "[yellow]No automated access to Webook[/yellow]\n"
            "[red]Payment and final purchase remain under user control[/red]",
            title="Safety Controls",
            border_style="green",
        )
    )