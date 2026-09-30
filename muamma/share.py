from datetime import UTC, date

from flask import url_for

from muamma import clock
from muamma.models import Play, Puzzle, utcnow
from muamma.timing import opened_at


def _as_utc(value):
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def duration_between(started, finished) -> int | None:
    """Whole seconds between two timestamps, whatever their tzinfo."""
    if started is None or finished is None:
        return None
    return max(0, int((_as_utc(finished) - _as_utc(started)).total_seconds()))


def play_duration(play: Play) -> int | None:
    """Seconds between the page opening and the puzzle being finished."""
    return duration_between(play.started_at, play.finished_at)


def share_text(puzzle: Puzzle, play: Play, streak: int, url: str) -> str | None:
    """Spoiler-free result summary for a finished daily puzzle."""
    if puzzle.kind != "daily" or play.status == "in_progress":
        return None

    lines = [f"Muamma · {puzzle.publish_date:%d.%m.%Y}"]
    if play.status == "solved":
        lines.append(f"✅ {play.guess_count}. tahminde çözdüm")
        assists = []
        if play.hints_used:
            assists.append(f"💡 {play.hints_used} ipucu")
        if play.letters_revealed:
            assists.append(f"🔤 {play.letters_revealed} harf")
        lines.append(" · ".join(assists) if assists else "🧠 Yardımsız")
    else:
        lines.append("❌ Cevaba baktım")

    if streak:
        lines.append(f"🔥 Seri: {streak}")
    lines.append(url)
    return "\n".join(lines)


def elapsed_seconds(puzzle: Puzzle, play: Play | None) -> int:
    """Seconds since the page was opened, frozen once the puzzle is finished."""
    if play is not None and play.status != "in_progress":
        return play_duration(play) or 0

    started = play.started_at if play is not None else opened_at(puzzle.id)
    if started is None:
        return 0
    return max(0, int((utcnow() - _as_utc(started)).total_seconds()))


def finish_details(puzzle: Puzzle, play: Play, streak: int, today: date) -> dict:
    """Share text and countdown shown after a puzzle is finished."""
    is_today = puzzle.kind == "daily" and puzzle.publish_date == today
    return {
        "share": share_text(puzzle, play, streak, url_for("main.index", _external=True)),
        "next_in": clock.seconds_until_tomorrow() if is_today else None,
        "duration": play_duration(play),
    }