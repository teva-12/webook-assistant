from app.core.models import BookingStage
from app.booking.safety_guard import can_continue
from app.monitoring.stage_tracker import StageTracker
from app.reporting.report_builder import build_report
from app.reporting.report_writer import save_report


STAGE_OPTIONS = {
    "1": BookingStage.READY,
    "2": BookingStage.WAITING_FOR_USER,
    "3": BookingStage.TICKET_SELECTION,
    "4": BookingStage.CHECKOUT,
}


def main():
    tracker = StageTracker()
    tracker.start(BookingStage.READY)

    print("\nWebook Booking Assistant")
    print("Manual session tracking started.")
    print("1. Ready")
    print("2. Waiting for user")
    print("3. Ticket selection")
    print("4. Checkout reached (safety stop)")
    print("Q. Finish session")

    while True:
        choice = input("\nEnter stage: ").strip().lower()

        if choice == "q":
            tracker.stop()
            break

        next_stage = STAGE_OPTIONS.get(choice)

        if next_stage is None:
            print("Invalid option.")
            continue

        tracker.transition(next_stage)

        if not can_continue(next_stage):
            print("Safety stop: no further steps will be performed.")
            tracker.stop()
            break

        print(f"Stage recorded: {next_stage.value}")

    report = build_report(tracker.records)
    report_path = save_report(report)

    print("\nSession finished.")
    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()