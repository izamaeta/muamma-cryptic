from datetime import date

from sqlalchemy import select

from muamma.cache import cached
from muamma.extensions import db
from muamma.models import Play, Puzzle
from muamma.share import duration_between

MIN_SOLVERS = 20
CACHE_SECONDS = 300


def _median(values: list[int]) -> int:
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) // 2


def _compute(puzzle: Puzzle) -> dict | None:
    rows = db.session.execute(
        select(Play.guess_count, Play.started_at, Play.finished_at).where(
            Play.puzzle_id == puzzle.id, Play.status == "solved"
        )
    ).all()
    if len(rows) < MIN_SOLVERS:
        return None

    seconds = sorted(
        taken
        for taken in (duration_between(row.started_at, row.finished_at) for row in rows)
        if taken is not None
    )
    return {
        "guesses": sum(row.guess_count for row in rows) / len(rows),
        # median, so a player who left the tab open all day does not move it
        "seconds": _median(seconds) if seconds else 0,
    }


def community_stats(puzzle: Puzzle) -> dict | None:
    """Solvers' mean guess count and median time, or None below the threshold."""
    return cached(f"community:{puzzle.id}", CACHE_SECONDS, lambda: _compute(puzzle))


def _guesses_text(mean: float) -> str:
    return f"{mean:.1f}".replace(".", ",")


def _in_time_text(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours} sa {minutes} dk'da"
    if minutes:
        return f"{minutes} dk {secs} sn'de"
    return f"{secs} sn'de"


def community_line(puzzle: Puzzle, today: date) -> str | None:
    """One line about everyone who solved this puzzle, share-text style."""
    stats = community_stats(puzzle)
    if stats is None:
        return None

    on_its_day = puzzle.kind == "daily" and puzzle.publish_date == today
    who = "Bugün çözenler" if on_its_day else "Bu muammayı çözenler"
    return (
        f"{who} ortalama {_guesses_text(stats['guesses'])} tahminde, "
        f"genelde {_in_time_text(stats['seconds'])} çözdü."
    )
