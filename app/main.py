
from time import monotonic

from app.core.models import BookingStage
from app.booking.safety_guard import can_continue
from app.monitoring.stage_tracker import StageTracker
from app.monitoring.stage_transitions import InvalidTransitionError
from app.reporting.report_builder import build_report
from app.reporting.report_writer import save_report, save_html_report
from app.ui.dashboard import display_dashboard


STAGE_OPTIONS = {
    "1": BookingStage.READY,
    "2": BookingStage.WAITING_FOR_USER,
    "3": BookingStage.TICKET_SELECTION,
    "4": BookingStage.CHECKOUT,
}


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

        print("\n[1] Ready")
        print("[2] Waiting for user")
        print("[3] Ticket selection")
        print("[4] Checkout (Safety Stop)")
        print("[Q] Finish session")

        choice = input("\nSelect stage: ").strip().lower()

        if choice == "q":
            tracker.stop()
            break

        next_stage = STAGE_OPTIONS.get(choice)

        if next_stage is None:
            print("Invalid option.")
            input("Press Enter to continue...")
            continue

        try:
            tracker.transition(next_stage)
        except InvalidTransitionError as error:
            print(error)
            input("Press Enter to continue...")
            continue

        current_stage = next_stage
        stage_started_at = monotonic()

        if not can_continue(current_stage):
            display_dashboard(
                current_stage=current_stage.value,
                elapsed_seconds=0,
                status="Safety Stop",
            )
            print("\nSafety stop activated.")
            tracker.stop()
            break

    # Generate reports once, after the session ends.
    report = build_report(tracker.records)

    report_path = save_report(report)
    html_report_path = save_html_report(report)

    print("\nSession finished successfully.")
    print(f"JSON Report: {report_path}")
    print(f"HTML Report: {html_report_path}")


if __name__ == "__main__":
    main()
