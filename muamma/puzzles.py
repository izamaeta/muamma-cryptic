from datetime import date

from sqlalchemy import select

from muamma.extensions import db
from muamma.models import Puzzle
from muamma.text import normalize_answer


def daily_puzzle_for(day: date) -> Puzzle | None:
    return db.session.scalar(
        select(Puzzle).where(
            Puzzle.kind == "daily",
            Puzzle.status == "ready",
            Puzzle.publish_date == day,
        )
    )


def is_playable(puzzle: Puzzle, today: date) -> bool:
    """Ready puzzles only; daily puzzles only from their publish date on."""
    if puzzle.status != "ready":
        return False
    if puzzle.kind == "daily":
        return puzzle.publish_date <= today
    return True


def answer_length(enumeration: str) -> int:
    return sum(int(part) for part in enumeration.replace("-", ",").split(","))


def check_answer(puzzle: Puzzle, guess: str) -> bool:
    return normalize_answer(guess) == normalize_answer(puzzle.answer)