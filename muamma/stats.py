from datetime import date

from sqlalchemy import func, select

from muamma.extensions import db
from muamma.models import Play, Player, Puzzle


def player_stats(player: Player, today: date) -> dict:
    rows = db.session.execute(
        select(Puzzle.kind, Play.status, func.count())
        .select_from(Play)
        .join(Play.puzzle)
        .where(Play.player_id == player.id, Play.status != "in_progress")
        .group_by(Puzzle.kind, Play.status)
    ).all()
    counts = {(kind, status): n for kind, status, n in rows}

    daily_solved = counts.get(("daily", "solved"), 0)
    daily_played = daily_solved + counts.get(("daily", "revealed"), 0)

    return {
        "daily_played": daily_played,
        "daily_solved": daily_solved,
        "solve_rate": round(100 * daily_solved / daily_played) if daily_played else 0,
        "current_streak": player.displayed_streak(today),
        "max_streak": player.max_streak,
        "practice_solved": counts.get(("practice", "solved"), 0),
    }