from datetime import date

from sqlalchemy import select

from muamma.extensions import db
from muamma.models import Play, Puzzle
from muamma.text import normalize_answer, turkish_upper
from muamma.share import finish_details

def daily_puzzle_for(day: date) -> Puzzle | None:
    return db.session.scalar(
        select(Puzzle).where(
            Puzzle.kind == "daily",
            Puzzle.status == "ready",
            Puzzle.publish_date == day,
        )
    )


def archive_puzzles(today: date) -> list[Puzzle]:
    """Ready daily puzzles already published, newest first."""
    return list(
        db.session.scalars(
            select(Puzzle)
            .where(
                Puzzle.kind == "daily",
                Puzzle.status == "ready",
                Puzzle.publish_date < today,
            )
            .order_by(Puzzle.publish_date.desc())
        )
    )


def archive_neighbours(day: date, today: date) -> tuple[Puzzle | None, Puzzle | None]:
    """Nearest published daily puzzles before and after a date."""
    base = select(Puzzle).where(Puzzle.kind == "daily", Puzzle.status == "ready")
    previous = db.session.scalar(
        base.where(Puzzle.publish_date < day)
        .order_by(Puzzle.publish_date.desc())
        .limit(1)
    )
    following = db.session.scalar(
        base.where(Puzzle.publish_date > day, Puzzle.publish_date <= today)
        .order_by(Puzzle.publish_date)
        .limit(1)
    )
    return previous, following


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

def tile_groups(puzzle: Puzzle, revealed: int) -> list[list[str]]:
    """Answer letters grouped by word; unrevealed positions are empty."""
    letters = normalize_answer(puzzle.answer)
    groups, start = [], 0
    for size in enumeration_parts(puzzle.enumeration):
        groups.append([letters[i] if i < revealed else "" for i in range(start, start + size)])
        start += size
    return groups


def letter_pattern(puzzle: Puzzle, revealed: int) -> str:
    groups = tile_groups(puzzle, revealed)
    return " ".join("".join(ch or "_" for ch in group) for group in groups)


def clue_parts(puzzle: Puzzle) -> tuple[str, str, str] | None:
    """Split the clue around its definition, matching Turkish case rules."""
    if not puzzle.definition:
        return None
    upper_clue = turkish_upper(puzzle.clue)
    if len(upper_clue) != len(puzzle.clue):
        return None
    start = upper_clue.find(turkish_upper(puzzle.definition))
    if start < 0:
        return None
    end = start + len(puzzle.definition)
    return puzzle.clue[:start], puzzle.clue[start:end], puzzle.clue[end:]


def puzzle_view(puzzle: Puzzle, play: Play | None, today: date) -> dict:
    """Template context for a puzzle, restoring the player's progress."""
    finished = play is not None and play.status != "in_progress"
    hints_used = play.hints_used if play else 0
    revealed = play.letters_revealed if play else 0
    shown = answer_length(puzzle.enumeration) if finished else revealed

    details = {"share": None, "next_in": None}
    if finished:
        details = finish_details(puzzle, play, play.player.displayed_streak(today), today)

    return {
        "puzzle": puzzle,
        "play": play,
        "used_hints": hint_texts(puzzle)[:hints_used],
        "tiles": tile_groups(puzzle, shown),
        "pattern": letter_pattern(puzzle, revealed) if revealed and not finished else None,
        "highlight": clue_parts(puzzle) if finished or hints_used else None,
        "streak_risk": puzzle.kind == "daily" and puzzle.publish_date == today,
        **details,
    }