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
    entries = [(key, value) for key, value in _stored().items() if key != str(puzzle_id)]
    entries.append((str(puzzle_id), datetime.now(UTC).timestamp()))
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
