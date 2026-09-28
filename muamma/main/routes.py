from flask import render_template

from muamma import clock
from muamma.gameplay import get_play
from muamma.main import bp
from muamma.players import current_player
from muamma.puzzles import daily_puzzle_for


@bp.get("/")
def index():
    today = clock.today()
    puzzle = daily_puzzle_for(today)
    player = current_player()
    play = get_play(player, puzzle) if puzzle else None
    streak = player.displayed_streak(today) if player else 0
    return render_template("index.html", puzzle=puzzle, play=play, streak=streak)


@bp.get("/health")
def health():
    return {"status": "ok"}