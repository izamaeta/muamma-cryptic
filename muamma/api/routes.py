from flask import abort, jsonify, request

from muamma import clock
from muamma.api import bp
from muamma.extensions import db
from muamma.gameplay import finish_play, get_or_create_play, log_event
from muamma.models import Puzzle
from muamma.players import current_player
from muamma.puzzles import answer_length, check_answer, is_playable
from muamma.text import normalize_answer

MAX_GUESS_LENGTH = 64


def _playable_or_404(puzzle_id, today):
    puzzle = db.session.get(Puzzle, puzzle_id)
    if puzzle is None or not is_playable(puzzle, today):
        abort(404)
    return puzzle


@bp.post("/puzzles/<int:puzzle_id>/guess")
def guess(puzzle_id):
    today = clock.today()
    puzzle = _playable_or_404(puzzle_id, today)

    payload = request.get_json(silent=True)
    raw = payload.get("guess") if isinstance(payload, dict) else None
    if not isinstance(raw, str) or len(raw) > MAX_GUESS_LENGTH:
        return jsonify(error="invalid_guess"), 400

    if len(normalize_answer(raw)) != answer_length(puzzle.enumeration):
        return jsonify(error="wrong_length"), 400

    player = current_player(create=True)
    play = get_or_create_play(player, puzzle)
    if play.status != "in_progress":
        return jsonify(error="finished"), 409

    correct = check_answer(puzzle, raw)
    play.guess_count += 1
    log_event(player, puzzle, "guess", guess=normalize_answer(raw), correct=correct)

    if not correct:
        db.session.commit()
        return jsonify(correct=False)

    finish_play(play, "solved", today)
    log_event(
        player,
        puzzle,
        "solve",
        guesses=play.guess_count,
        hints=play.hints_used,
        letters=play.letters_revealed,
    )
    db.session.commit()

    return jsonify(
        correct=True,
        answer=puzzle.answer,
        explanation=puzzle.explanation,
        streak=player.displayed_streak(today),
    )