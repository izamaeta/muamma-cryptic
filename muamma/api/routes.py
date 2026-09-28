from flask import abort, jsonify, request

from muamma import clock
from muamma.api import bp
from muamma.extensions import db
from muamma.gameplay import finish_play, get_or_create_play, log_event
from muamma.models import Puzzle
from muamma.players import current_player
from muamma.puzzles import (
    answer_length,
    check_answer,
    hint_texts,
    is_playable,
    letter_pattern,
)
from muamma.text import normalize_answer

MAX_GUESS_LENGTH = 64


@bp.errorhandler(404)
def not_found(error):
    return jsonify(error="not_found"), 404


@bp.errorhandler(409)
def conflict(error):
    return jsonify(error=error.description), 409


def _playable_or_404(puzzle_id, today):
    puzzle = db.session.get(Puzzle, puzzle_id)
    if puzzle is None or not is_playable(puzzle, today):
        abort(404)
    return puzzle


def _active_play(puzzle):
    player = current_player(create=True)
    play = get_or_create_play(player, puzzle)
    if play.status != "in_progress":
        abort(409, description="finished")
    return player, play


def _solution(puzzle, player, today):
    return {
        "answer": puzzle.answer,
        "explanation": puzzle.explanation,
        "streak": player.displayed_streak(today),
    }


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

    player, play = _active_play(puzzle)

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
    return jsonify(correct=True, **_solution(puzzle, player, today))


@bp.post("/puzzles/<int:puzzle_id>/hint")
def hint(puzzle_id):
    puzzle = _playable_or_404(puzzle_id, clock.today())
    player, play = _active_play(puzzle)

    hints = hint_texts(puzzle)
    if play.hints_used >= len(hints):
        abort(409, description="no_more_hints")

    text = hints[play.hints_used]
    play.hints_used += 1
    log_event(player, puzzle, "hint", level=play.hints_used)
    db.session.commit()
    return jsonify(text=text, remaining=len(hints) - play.hints_used)


@bp.post("/puzzles/<int:puzzle_id>/letter")
def letter(puzzle_id):
    puzzle = _playable_or_404(puzzle_id, clock.today())
    player, play = _active_play(puzzle)

    if play.letters_revealed >= answer_length(puzzle.enumeration) - 1:
        abort(409, description="no_more_letters")

    play.letters_revealed += 1
    log_event(player, puzzle, "reveal_letter", count=play.letters_revealed)
    db.session.commit()
    return jsonify(pattern=letter_pattern(puzzle, play.letters_revealed))


@bp.post("/puzzles/<int:puzzle_id>/reveal")
def reveal(puzzle_id):
    today = clock.today()
    puzzle = _playable_or_404(puzzle_id, today)
    player, play = _active_play(puzzle)

    finish_play(play, "revealed", today)
    log_event(player, puzzle, "reveal_answer")
    db.session.commit()
    return jsonify(**_solution(puzzle, player, today))