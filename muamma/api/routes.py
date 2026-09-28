from flask import abort, jsonify, request

from muamma import clock
from muamma.api import bp
from muamma.extensions import db
from muamma.models import Puzzle
from muamma.puzzles import answer_length, check_answer, is_playable
from muamma.text import normalize_answer

MAX_GUESS_LENGTH = 64


@bp.post("/puzzles/<int:puzzle_id>/guess")
def guess(puzzle_id):
    puzzle = db.session.get(Puzzle, puzzle_id)
    if puzzle is None or not is_playable(puzzle, clock.today()):
        abort(404)

    payload = request.get_json(silent=True)
    raw = payload.get("guess") if isinstance(payload, dict) else None
    if not isinstance(raw, str) or len(raw) > MAX_GUESS_LENGTH:
        return jsonify(error="invalid_guess"), 400

    if len(normalize_answer(raw)) != answer_length(puzzle.enumeration):
        return jsonify(error="wrong_length"), 400

    if not check_answer(puzzle, raw):
        return jsonify(correct=False)

    return jsonify(correct=True, answer=puzzle.answer, explanation=puzzle.explanation)