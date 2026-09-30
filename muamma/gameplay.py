from datetime import date, timedelta

from sqlalchemy import func, select

from muamma.extensions import db
from muamma.models import Event, Play, Player, Puzzle, utcnow
from muamma.timing import opened_at


def get_play(player: Player | None, puzzle: Puzzle) -> Play | None:
    if player is None:
        return None
    return db.session.scalar(
        select(Play).where(Play.player_id == player.id, Play.puzzle_id == puzzle.id)
    )


def play_status_by_puzzle(player: Player | None) -> dict[int, str]:
    """Every play of this player, as puzzle id to status, in one query."""
    if player is None:
        return {}
    rows = db.session.execute(
        select(Play.puzzle_id, Play.status).where(Play.player_id == player.id)
    ).all()
    return dict(rows)


def get_or_create_play(player: Player, puzzle: Puzzle) -> Play:
    play = get_play(player, puzzle)
    if play is None:
        play = Play(
            player=player,
            puzzle=puzzle,
            status="in_progress",
            guess_count=0,
            hints_used=0,
            letters_revealed=0,
            counts_for_streak=False,
            started_at=opened_at(puzzle.id) or utcnow(),
        )
        db.session.add(play)
    return play


def wrong_guesses(play: Play) -> list[str]:
    """This player's incorrect guesses for this puzzle, oldest first."""
    events = db.session.scalars(
        select(Event)
        .where(
            Event.player_id == play.player_id,
            Event.puzzle_id == play.puzzle_id,
            Event.type == "guess",
        )
        .order_by(Event.created_at, Event.id)
    )
    return [
        event.data["guess"]
        for event in events
        if not event.data.get("correct") and event.data.get("guess")
    ]


def log_event(player: Player, puzzle: Puzzle | None, type_: str, **data) -> None:
    db.session.add(
        Event(
            player_id=player.id,
            puzzle_id=puzzle.id if puzzle else None,
            type=type_,
            data=data,
        )
    )


def record_daily_solve(player: Player, day: date) -> None:
    """Advance the streak for a daily puzzle solved on its publish date."""
    if player.last_streak_date == day:
        return
    if player.last_streak_date == day - timedelta(days=1):
        player.current_streak += 1
    else:
        player.current_streak = 1
    player.max_streak = max(player.max_streak, player.current_streak)
    player.last_streak_date = day


def finish_play(play: Play, status: str, today: date) -> None:
    play.status = status
    play.finished_at = utcnow()

    puzzle = play.puzzle
    on_its_day = puzzle.kind == "daily" and puzzle.publish_date == today

    if status == "solved" and on_its_day:
        play.counts_for_streak = True
        record_daily_solve(play.player, today)
    elif status == "revealed" and on_its_day:
        play.player.current_streak = 0

def random_practice_id(player: Player | None, technique: str | None = None) -> int | None:
    """Random ready practice puzzle the player has not finished.

    An unknown technique simply matches nothing, so the caller can fall
    back without keeping a list of valid values in step.
    """
    query = select(Puzzle.id).where(Puzzle.kind == "practice", Puzzle.status == "ready")
    if technique:
        query = query.where(Puzzle.technique == technique)
    if player is not None:
        finished = select(Play.puzzle_id).where(
            Play.player_id == player.id, Play.status != "in_progress"
        )
        query = query.where(Puzzle.id.not_in(finished))
    return db.session.scalar(query.order_by(func.random()).limit(1))