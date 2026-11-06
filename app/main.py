
from time import monotonic

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from app.core.models import BookingStage
from app.booking.safety_guard import can_continue
from app.monitoring.stage_tracker import StageTracker
from app.monitoring.stage_transitions import InvalidTransitionError
from app.reporting.report_builder import build_report
from app.reporting.report_writer import save_report, save_html_report
from app.ui.dashboard import display_dashboard


console = Console()

STAGE_OPTIONS = {
    "1": BookingStage.READY,
    "2": BookingStage.WAITING_FOR_USER,
    "3": BookingStage.TICKET_SELECTION,
    "4": BookingStage.CHECKOUT,
}


def display_menu():
    menu = Table(
        title="SESSION CONTROLS",
        box=box.ROUNDED,
        expand=True,
        border_style="cyan",
    )

    menu.add_column("Option", style="bold cyan", justify="center")
    menu.add_column("Action", style="white")

    menu.add_row("1", "Ready")
    menu.add_row("2", "Waiting for user")
    menu.add_row("3", "Ticket selection")
    menu.add_row("4", "Checkout — Safety Stop")
    menu.add_row("Q", "Finish session")

    console.print(menu)


def main():
    tracker = StageTracker()
    current_stage = BookingStage.READY

    tracker.start(current_stage)
    stage_started_at = monotonic()

    while True:
        elapsed = monotonic() - stage_started_at

        display_dashboard(
            current_stage=current_stage.value,
            elapsed_seconds=elapsed,
            status=(
                "Tracking"
                if current_stage != BookingStage.CHECKOUT
                else "Safety Stop"
            ),
        )

        display_menu()

        choice = Prompt.ask(
            "\n[bold cyan]Select an action[/]",
            default="Q",
        ).strip().lower()

        if choice == "q":
            tracker.stop()
            break

        next_stage = STAGE_OPTIONS.get(choice)

        if next_stage is None:
            console.print(
                Panel(
                    "[bold red]Invalid option. Please choose 1, 2, 3, 4, or Q.[/]",
                    border_style="red",
                )
            )
            Prompt.ask("Press Enter to continue", default="")
            continue

        try:
            tracker.transition(next_stage)
        except InvalidTransitionError as error:
            console.print(
                Panel(
                    f"[bold yellow]{error}[/]",
                    title="Stage Transition Notice",
                    border_style="yellow",
                )
            )
            Prompt.ask("Press Enter to continue", default="")
            continue

        current_stage = next_stage
        stage_started_at = monotonic()

        if not can_continue(current_stage):
            console.print(
                Panel(
                    "[bold red]Safety stop activated.[/]\n"
                    "The session will end here. No payment or purchase will be performed.",
                    title="Checkout Safety Stop",
                    border_style="red",
                )
            )
            tracker.stop()
            break

    report = build_report(tracker.records)

    report_path = save_report(report)
    html_report_path = save_html_report(report)

    console.print(
        Panel(
            "[bold green]Session finished successfully.[/]\n\n"
            f"JSON Report: {report_path}\n"
            f"HTML Report: {html_report_path}",
            title="Session Summary",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
