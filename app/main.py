
import webbrowser
from time import monotonic

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from app.core.models import BookingStage, BookingPreferences
from app.core.config import settings, validate_settings
from app.booking.category_policy import (
    CategoryAvailability,
    choose_category,
)
from app.booking.safety_guard import can_continue
from app.browser.launcher import open_event_page
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
    menu.add_row("4", "Checkout - Safety Stop")
    menu.add_row("5", "Open official Webook event page")
    menu.add_row("6", "Evaluate ticket availability")
    menu.add_row("Q", "Finish session")

    console.print(menu)


def ask_ticket_count(category_name: str) -> int:
    while True:
        count = IntPrompt.ask(
            f"How many {category_name} tickets are available?",
            default=0,
        )

        if count >= 0:
            return count

        console.print("[red]Please enter zero or a positive number.[/]")


def evaluate_ticket_options() -> dict:
    console.print(
        Panel(
            "Enter the availability you can currently see "
            "on the official Webook page.\n"
            "This tool does not read or control the website.",
            title="Ticket Availability",
            border_style="cyan",
        )
    )

    bronze_count = ask_ticket_count("Bronze")
    bronze_adjacent = False

    if bronze_count >= 2:
        bronze_adjacent = Confirm.ask(
            "Are at least two Bronze seats next to each other?",
            default=False,
        )

    silver_count = ask_ticket_count("Silver")
    silver_adjacent = False

    if silver_count >= 2:
        silver_adjacent = Confirm.ask(
            "Are at least two Silver seats next to each other?",
            default=False,
        )

    preferences = BookingPreferences()

    decision = choose_category(
        bronze=CategoryAvailability(
            available_tickets=bronze_count,
            adjacent_seats_available=bronze_adjacent,
        ),
        silver=CategoryAvailability(
            available_tickets=silver_count,
            adjacent_seats_available=silver_adjacent,
        ),
        preferences=preferences,
    )

    approved = False

    console.print()
    console.print(
        Panel(
            decision.reason,
            title="Selection Recommendation",
            border_style="cyan",
        )
    )

    if decision.category is None:
        console.print(
            "[bold red]No suitable category found for two adjacent tickets.[/]"
        )
        result = "no_suitable_category"

    elif decision.requires_approval:
        console.print(
            f"[yellow]Recommended fallback: {decision.category.value.upper()}[/]"
        )

        approved = Confirm.ask(
            "Do you approve using Silver instead of Bronze?",
            default=False,
        )

        if approved:
            result = "approved"
            console.print(
                Panel(
                    "SILVER is approved as the preferred option.\n"
                    "Please select the two adjacent seats yourself on Webook.",
                    title="User Decision",
                    border_style="green",
                )
            )
        else:
            result = "rejected"
            console.print(
                "[yellow]Silver was not approved. No category selected.[/]"
            )

    else:
        approved = True
        result = "approved"

        console.print(
            Panel(
                f"{decision.category.value.upper()} is approved as the preferred option.\n"
                "Please select the two adjacent seats yourself on Webook.",
                title="User Decision",
                border_style="green",
            )
        )

    return {
        "quantity_requested": preferences.quantity,
        "preferred_category": preferences.preferred_category.value,
        "fallback_category": preferences.fallback_category.value,
        "bronze_available_count": bronze_count,
        "bronze_adjacent_seats": bronze_adjacent,
        "silver_available_count": silver_count,
        "silver_adjacent_seats": silver_adjacent,
        "recommended_category": (
            decision.category.value if decision.category else None
        ),
        "approval_required": decision.requires_approval,
        "user_approved": approved,
        "result": result,
        "reason": decision.reason,
        "recorded_at": __import__("datetime").datetime.now().astimezone().isoformat(),
        "manual_input": True,
    }


def main():
    try:
        validate_settings()
    except ValueError as error:
        console.print(
            Panel(
                f"[bold red]Configuration error:[/]\n{error}",
                border_style="red",
            )
        )
        return

    tracker = StageTracker()
    current_stage = BookingStage.READY
    ticket_evaluations = []

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
            event_name=settings.event_name,
            event_url=settings.event_url,
            release_at=settings.ticket_release_at,
        )

        display_menu()

        choice = Prompt.ask(
            "\n[bold cyan]Select an action[/]",
            default="Q",
        ).strip().lower()

        if choice == "q":
            tracker.stop()
            break

        if choice == "5":
            try:
                opened = open_event_page(settings.event_url)

                if opened:
                    console.print(
                        "[bold green]Official event page opened in your browser.[/]"
                    )
                else:
                    console.print(
                        "[bold yellow]Could not open the browser automatically.[/]"
                    )

            except (ValueError, webbrowser.Error) as error:
                console.print(
                    f"[bold red]Could not open event page: {error}[/]"
                )

            Prompt.ask("Press Enter to return to the dashboard", default="")
            continue

        if choice == "6":
            if current_stage != BookingStage.TICKET_SELECTION:
                console.print(
                    "[yellow]Move to Ticket Selection first (option 3).[/]"
                )
            else:
                evaluation = evaluate_ticket_options()
                ticket_evaluations.append(evaluation)

            Prompt.ask("Press Enter to return to the dashboard", default="")
            continue

        next_stage = STAGE_OPTIONS.get(choice)

        if next_stage is None:
            console.print(
                Panel(
                    "[bold red]Invalid option. Please choose 1, 2, 3, 4, 5, 6, or Q.[/]",
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
                    "No payment or purchase will be performed.",
                    title="Checkout Safety Stop",
                    border_style="red",
                )
            )
            tracker.stop()
            break

    report = build_report(
        tracker.records,
        ticket_evaluations=ticket_evaluations,
    )

    report_path = save_report(report)
    html_report_path = save_html_report(report)

    console.print(
        Panel(
            "[bold green]Session ended. Report generated.[/]\n\n"
            f"JSON Report: {report_path}\n"
            f"HTML Report: {html_report_path}",
            title="Session Summary",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
