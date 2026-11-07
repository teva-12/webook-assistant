from datetime import datetime
from time import monotonic
from urllib.parse import urlparse

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from app.core.models import BookingStage, BookingPreferences, TicketCategory
from app.core.config import settings, validate_settings
from app.booking.category_policy import CategoryAvailability, choose_category
from app.booking.safety_guard import can_continue
from app.browser.launcher import (
    open_event_page,
    inspect_visible_event_page,
    close_browser,
    validate_event_url,
)
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

CATEGORY_BY_NAME = {item.value.title(): item for item in TicketCategory}


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
    menu.add_row("2", "Waiting for user / official queue")
    menu.add_row("3", "Ticket selection stage")
    menu.add_row("4", "Checkout handoff - Safety Stop")
    menu.add_row("5", "Open / focus persistent Webook browser")
    menu.add_row("6", "Set preferences + evaluate visible availability")
    menu.add_row("7", "Expand ticket types + inspect event page")
    menu.add_row("8", "Change event link")
    menu.add_row("Q", "Finish session")
    console.print(menu)


def ask_ticket_count(category_name: str) -> int:
    while True:
        count = IntPrompt.ask(
            f"How many {category_name} tickets can you see?",
            default=0,
        )
        if count >= 0:
            return count
        console.print("[red]Please enter zero or a positive number.[/]")


def choose_from_visible_categories(inspection_categories: list[str], prompt_label: str) -> TicketCategory:
    available_names = [name for name in inspection_categories if name in CATEGORY_BY_NAME]
    if not available_names:
        available_names = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Royal"]
        console.print("[yellow]No inspected category list yet; using the standard category names. Check the live page before proceeding.[/]")

    selected = Prompt.ask(
        prompt_label,
        choices=available_names,
        default="Bronze" if "Bronze" in available_names else available_names[0],
    )
    return CATEGORY_BY_NAME[selected]


def evaluate_ticket_options(inspection_categories: list[str]) -> dict:
    console.print(
        Panel(
            "Choose your request. Availability and adjacency must be confirmed by you "
            "on the visible official seat map. This screen only evaluates the facts you enter.",
            title="Booking Preferences",
            border_style="cyan",
        )
    )

    quantity = IntPrompt.ask("How many tickets do you want? (1-3)", default=2)
    while quantity not in (1, 2, 3):
        console.print("[red]Quantity must be 1, 2, or 3.[/]")
        quantity = IntPrompt.ask("How many tickets do you want? (1-3)", default=2)

    zone = Prompt.ask("Preferred area / section (e.g. Area 2)", default="Area 2").strip()
    preferred = choose_from_visible_categories(inspection_categories, "Preferred ticket category")

    fallback_candidates = [name for name in inspection_categories if name in CATEGORY_BY_NAME and CATEGORY_BY_NAME[name] != preferred]
    if not fallback_candidates:
        fallback_candidates = [name for name in ("Silver", "Gold", "Platinum", "Diamond", "Royal", "Bronze") if CATEGORY_BY_NAME[name] != preferred]
    fallback_default = "Silver" if "Silver" in fallback_candidates else fallback_candidates[0]
    fallback_name = Prompt.ask(
        "Fallback category (requires your approval)",
        choices=fallback_candidates,
        default=fallback_default,
    )
    fallback = CATEGORY_BY_NAME[fallback_name]

    adjacent_required = quantity > 1 and Confirm.ask(
        "Must all requested seats be adjacent?", default=True
    )
    preferences = BookingPreferences(
        quantity=quantity,
        preferred_category=preferred,
        fallback_category=fallback,
        preferred_zone=zone or None,
        require_adjacent_seats=adjacent_required,
    )

    candidates = list(dict.fromkeys([preferred, fallback]))
    availability = {}
    raw_counts = {}
    for category in candidates:
        count = ask_ticket_count(category.value.title())
        adjacent = False
        if quantity == 1 and count >= 1:
            adjacent = True
        elif quantity > 1 and adjacent_required and count >= quantity:
            adjacent = Confirm.ask(
                f"Did you visually confirm {quantity} adjacent {category.value.title()} seats in {zone or 'the chosen area'}?",
                default=False,
            )
        elif quantity > 1 and not adjacent_required and count >= quantity:
            adjacent = True

        availability[category] = CategoryAvailability(
            available_tickets=count,
            adjacent_seats_available=adjacent,
        )
        raw_counts[category.value] = {
            "visible_count_entered_by_user": count,
            "adjacency_confirmed_by_user": adjacent,
        }

    decision = choose_category(
        preferences=preferences,
        availability_by_category=availability,
    )

    console.print(Panel(decision.reason, title="Recommendation", border_style="cyan"))
    approved = False
    result = "no_suitable_category"

    if decision.category is None:
        console.print("[bold red]No suitable category matches your request.[/]")
    elif decision.requires_approval:
        console.print(
            f"[yellow]Fallback recommendation: {decision.category.value.title()}[/]"
        )
        approved = Confirm.ask(
            f"Approve switching from {preferred.value.title()} to {decision.category.value.title()}?",
            default=False,
        )
        result = "approved_fallback" if approved else "fallback_rejected"
    else:
        approved = Confirm.ask(
            f"Confirm {decision.category.value.title()} in {zone or 'the chosen area'} for {quantity} ticket(s)?",
            default=True,
        )
        result = "approved_preferred" if approved else "preferred_rejected"

    if approved:
        console.print(
            Panel(
                f"Preference confirmed: {decision.category.value.title()} · {quantity} ticket(s) · {zone or 'Any area'}\n"
                + ("Adjacent seats required.\n" if adjacent_required else "Adjacency not required.\n")
                + "Now select the seats yourself on the official Webook map. The app will not click seats or submit the booking.",
                title="Ready for Manual Seat Selection",
                border_style="green",
            )
        )

    return {
        "quantity_requested": quantity,
        "preferred_category": preferred.value,
        "fallback_category": fallback.value,
        "preferred_zone": zone,
        "require_adjacent_seats": adjacent_required,
        "availability_entered": raw_counts,
        "recommended_category": decision.category.value if decision.category else None,
        "approval_required": decision.requires_approval,
        "user_approved": approved,
        "result": result,
        "reason": decision.reason,
        "recorded_at": datetime.now().astimezone().isoformat(),
        "manual_input": True,
        "seat_selection_automated": False,
        "payment_is_manual": True,
    }


def update_event_link() -> None:
    new_url = Prompt.ask("Paste the official Webook event URL", default=settings.event_url).strip()
    try:
        validate_event_url(new_url)
    except ValueError as error:
        console.print(Panel(str(error), title="Invalid event link", border_style="red"))
        return

    settings.event_url = new_url
    proposed_name = Prompt.ask("Event label (optional)", default="").strip()
    if proposed_name:
        settings.event_name = proposed_name
    else:
        slug = urlparse(new_url).path.rstrip("/").split("/")[-1]
        settings.event_name = slug.replace("-", " ").title() or "Webook Event"

    console.print(
        Panel(
            f"Event link updated.\n{settings.event_name}\n{settings.event_url}\n\nThe next browser launch will open this event.",
            title="Event Updated",
            border_style="green",
        )
    )


def main():
    try:
        validate_settings()
    except ValueError as error:
        console.print(Panel(f"[bold red]Configuration error:[/]\n{error}", border_style="red"))
        return

    tracker = StageTracker()
    current_stage = BookingStage.READY
    ticket_evaluations = []
    page_inspections = []
    latest_categories: list[str] = []

    tracker.start(current_stage)
    stage_started_at = monotonic()

    try:
        while True:
            elapsed = monotonic() - stage_started_at
            display_dashboard(
                current_stage=current_stage.value,
                elapsed_seconds=elapsed,
                status="Tracking" if current_stage != BookingStage.CHECKOUT else "Safety Stop",
                event_name=settings.event_name,
                event_url=settings.event_url,
                release_at=settings.ticket_release_at,
            )
            display_menu()
            choice = Prompt.ask("\n[bold cyan]Select an action[/]", default="Q").strip().lower()

            if choice == "q":
                tracker.stop()
                break

            if choice == "8":
                update_event_link()
                Prompt.ask("Press Enter to return to the dashboard", default="")
                continue

            if choice == "5":
                try:
                    opened = open_event_page(settings.event_url)
                    if opened:
                        console.print(Panel(
                            "Official Webook event page opened in a visible persistent browser.\n"
                            "Sign in and complete any official queue steps yourself.\n"
                            "The app does not bypass queue controls or automate seat selection.",
                            title="Webook Browser Ready", border_style="green"
                        ))
                    else:
                        console.print("[bold yellow]Could not launch Chromium. Run: python -m playwright install chromium[/]")
                except ValueError as error:
                    console.print(f"[bold red]Could not open event page: {error}[/]")
                Prompt.ask("Press Enter to return to the dashboard", default="")
                continue

            if choice == "7":
                try:
                    inspection = inspect_visible_event_page()
                    page_inspections.append(inspection.to_dict())
                    latest_categories = [item.name for item in inspection.categories]
                    console.print(Panel(
                        f"Page: {inspection.page_title}\nInspected: {inspection.inspected_at}\n"
                        "Only visible event-page text is read; the first numbered ticket disclosure may be expanded.",
                        title="Ticket Types Inspection", border_style="cyan"
                    ))
                    if inspection.ticket_types_expand_clicked and inspection.ticket_types_expanded:
                        console.print("[green]Ticket categories disclosure expanded.[/]")
                    elif inspection.ticket_types_expand_clicked:
                        console.print("[yellow]Disclosure clicked, but no visible list update was detected.[/]")
                    elif inspection.ticket_types_expanded:
                        console.print("[green]Bronze and Silver are already visible.[/]")
                    else:
                        console.print("[dim]No numbered ticket disclosure detected.[/]")

                    if inspection.categories:
                        table = Table(title="Visible ticket categories", box=box.ROUNDED, expand=True)
                        table.add_column("Category")
                        table.add_column("Displayed price", justify="right")
                        table.add_column("Priority")
                        for item in inspection.categories:
                            priority = "PREFERRED" if item.name == "Bronze" else "FALLBACK" if item.name == "Silver" else "OPTION"
                            table.add_row(item.name, item.price_display, priority)
                        console.print(table)
                    else:
                        console.print("[yellow]No category/price pairs detected in visible page text.[/]")
                    console.print("[yellow]Displayed categories/prices do not prove live inventory or seat adjacency.[/]")
                except (RuntimeError, ValueError) as error:
                    console.print(Panel(str(error), title="Event page inspection", border_style="yellow"))
                Prompt.ask("Press Enter to return to the dashboard", default="")
                continue

            if choice == "6":
                if current_stage != BookingStage.TICKET_SELECTION:
                    console.print("[yellow]Move to Ticket Selection first (option 3).[/]")
                else:
                    ticket_evaluations.append(evaluate_ticket_options(latest_categories))
                Prompt.ask("Press Enter to return to the dashboard", default="")
                continue

            next_stage = STAGE_OPTIONS.get(choice)
            if next_stage is None:
                console.print(Panel("[bold red]Invalid option. Choose 1-8 or Q.[/]", border_style="red"))
                Prompt.ask("Press Enter to continue", default="")
                continue

            try:
                tracker.transition(next_stage)
            except InvalidTransitionError as error:
                console.print(Panel(f"[bold yellow]{error}[/]", title="Stage Transition Notice", border_style="yellow"))
                Prompt.ask("Press Enter to continue", default="")
                continue

            current_stage = next_stage
            stage_started_at = monotonic()

            if not can_continue(current_stage):
                console.print(Panel(
                    "[bold red]Payment handoff reached.[/]\n"
                    "The app stops here. Review the order and pay yourself on Webook.\n"
                    "Reaching this page is not proof that a booking is confirmed.",
                    title="Checkout Safety Stop", border_style="red"
                ))
                tracker.stop()
                break
    finally:
        close_browser()

    report = build_report(
        tracker.records,
        ticket_evaluations=ticket_evaluations,
        page_inspections=page_inspections,
    )
    report_path = save_report(report)
    html_report_path = save_html_report(report)
    console.print(Panel(
        "[bold green]Session ended. Report generated.[/]\n\n"
        f"JSON Report: {report_path}\nHTML Report: {html_report_path}",
        title="Session Summary", border_style="green"
    ))


if __name__ == "__main__":
    main()
