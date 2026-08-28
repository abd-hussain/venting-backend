"""
Run onboarding notification scheduled jobs.

Usage (from repo root, venv active):

    python -m scripts.run_onboarding_notifications

Intended for Heroku Scheduler (daily or hourly).
"""

from __future__ import annotations

from app.db.session import SessionLocal
from app.services.inbox_notifications import (
    run_book_first_session_reminders,
    run_complete_registration_job,
)


def main() -> None:
    db = SessionLocal()
    try:
        reg_count = run_complete_registration_job(db, inactive_hours=24)
        book_count = run_book_first_session_reminders(db, after_hours=48)
        print(
            f"Onboarding notifications: complete_registration={reg_count}, "
            f"book_first_session_reminders={book_count}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
