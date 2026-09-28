from datetime import date

from sqlalchemy import select

from muamma.extensions import db
from muamma.models import Play, Puzzle
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


def enumeration_parts(enumeration: str) -> list[int]:
    return [int(part) for part in enumeration.replace("-", ",").split(",")]


def answer_length(enumeration: str) -> int:
    return sum(enumeration_parts(enumeration))


def check_answer(puzzle: Puzzle, guess: str) -> bool:
    return normalize_answer(guess) == normalize_answer(puzzle.answer)


def hint_texts(puzzle: Puzzle) -> list[str]:
    """Definition first when the clue has one, then the puzzle's own hints."""
    first = [f"Tanım: {puzzle.definition}"] if puzzle.definition else []
    return [*first, *(puzzle.hints or [])]


def letter_pattern(puzzle: Puzzle, revealed: int) -> str:
    """Answer with the first `revealed` letters shown, grouped by word."""
    letters = normalize_answer(puzzle.answer)
    shown = [ch if i < revealed else "_" for i, ch in enumerate(letters)]

    groups, start = [], 0
    for size in enumeration_parts(puzzle.enumeration):
        groups.append("".join(shown[start : start + size]))
        start += size
    return " ".join(groups)


def puzzle_view(puzzle: Puzzle, play: Play | None, today: date) -> dict:
    """Template context for a puzzle, restoring the player's progress."""
    hints_used = play.hints_used if play else 0
    letters = play.letters_revealed if play else 0
    return {
        "puzzle": puzzle,
        "play": play,
        "used_hints": hint_texts(puzzle)[:hints_used],
        "pattern": letter_pattern(puzzle, letters) if letters else None,
        "streak_risk": puzzle.kind == "daily" and puzzle.publish_date == today,
    }