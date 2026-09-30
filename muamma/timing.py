from datetime import UTC, datetime, timedelta

from flask import has_request_context, session

SESSION_KEY = "opened"
KEPT_PUZZLES = 3
MAX_AGE = timedelta(hours=24)


def _stored() -> dict:
    if not has_request_context():
        return {}
    raw = session.get(SESSION_KEY)
    return raw if isinstance(raw, dict) else {}


def mark_opened(puzzle_id: int) -> None:
    """Remember in the session cookie when this puzzle page was opened."""
    if not has_request_context():
        return
    key = str(puzzle_id)
    stored = _stored()
    # an existing time is kept, so reloading the page does not restart the clock
    value = stored[key] if opened_at(puzzle_id) else datetime.now(UTC).timestamp()
    entries = [(other, when) for other, when in stored.items() if other != key]
    entries.append((key, value))
    session[SESSION_KEY] = dict(entries[-KEPT_PUZZLES:])


def opened_at(puzzle_id: int) -> datetime | None:
    """Stored open time, unless it is missing, older than a day or ahead of now."""
    value = _stored().get(str(puzzle_id))
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None

    try:
        when = datetime.fromtimestamp(value, UTC)
    except (OverflowError, OSError, ValueError):
        return None

    now = datetime.now(UTC)
    if when > now or now - when > MAX_AGE:
        return None
    return when
