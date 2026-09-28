from flask import render_template

from muamma import clock
from muamma.main import bp
from muamma.puzzles import daily_puzzle_for


@bp.get("/")
def index():
    puzzle = daily_puzzle_for(clock.today())
    return render_template("index.html", puzzle=puzzle)


@bp.get("/health")
def health():
    return {"status": "ok"}