"""Pure domain rules for travel dates, duration calculation, and day projection."""

from __future__ import annotations

from datetime import date, timedelta


def parse_iso_date(value: str | None) -> date | None:
    """Safely parse a string into an ISO date object."""
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None


def calculate_duration(
    start_date: str | date | None,
    end_date: str | date | None,
) -> tuple[int | None, int | None]:
    """Calculate (duration_days, duration_nights) from start and end dates.

    Rules:
    - If either date is missing or invalid: returns (None, None).
    - If end_date < start_date: returns (None, None).
    - duration_days = (end_date - start_date).days + 1
    - duration_nights = max(0, duration_days - 1)
    """
    start = parse_iso_date(start_date) if isinstance(start_date, str) else start_date
    end = parse_iso_date(end_date) if isinstance(end_date, str) else end_date

    if not start or not end:
        return None, None
    if end < start:
        return None, None

    days = (end - start).days + 1
    nights = max(0, days - 1)
    return days, nights


def date_for_itinerary_day(start_date: str | date | None, day_number: int | None) -> str | None:
    """Project the specific ISO date string (YYYY-MM-DD) for a given 1-indexed itinerary day."""
    start = parse_iso_date(start_date) if isinstance(start_date, str) else start_date
    if not start or not day_number or day_number < 1:
        return None
    target_date = start + timedelta(days=day_number - 1)
    return target_date.isoformat()


def format_travel_dates_label(
    start_date: str | date | None,
    end_date: str | date | None,
    fallback_text: str | None = None,
) -> str:
    """Format canonical travel date range string (e.g. '09 Nov 2026 – 20 Nov 2026')."""
    start = parse_iso_date(start_date) if isinstance(start_date, str) else start_date
    end = parse_iso_date(end_date) if isinstance(end_date, str) else end_date

    if not start or not end or end < start:
        return (fallback_text or "").strip()

    return f"{start:%d %b %Y} – {end:%d %b %Y}"
