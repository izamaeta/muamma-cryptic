from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from muamma.extensions import db
from muamma.models import Play, Puzzle
from muamma.puzzles import answer_length
from muamma.text import normalize_answer, turkish_upper

STOCK_WARNING_DAYS = 7
CALENDAR_DAYS = 14
LOCKED_FIELDS = ("kind", "status", "answer", "enumeration", "publish_date")


def has_plays(puzzle: Puzzle) -> bool:
    count = db.session.scalar(
        select(func.count()).select_from(Play).where(Play.puzzle_id == puzzle.id)
    )
    return count > 0


def is_locked(puzzle: Puzzle | None, today: date) -> bool:
    """Published or played puzzles keep their answer, kind, status and date."""
    if puzzle is None:
        return False
    published = (
        puzzle.kind == "daily" and puzzle.status == "ready" and puzzle.publish_date <= today
    )
    return published or has_plays(puzzle)


def lock_fields(form, puzzle: Puzzle) -> None:
    for name in LOCKED_FIELDS:
        getattr(form, name).data = getattr(puzzle, name)
    form.next_free_day.data = False


def next_free_day(today: date) -> date:
    taken = set(db.session.scalars(select(Puzzle.publish_date).where(Puzzle.publish_date >= today)))
    day = today
    while day in taken:
        day += timedelta(days=1)
    return day


def stock_days(today: date) -> int:
    """Consecutive days from today that have a ready daily puzzle."""
    ready = set(
        db.session.scalars(
            select(Puzzle.publish_date).where(
                Puzzle.kind == "daily",
                Puzzle.status == "ready",
                Puzzle.publish_date >= today,
            )
        )
    )
    days = 0
    while today + timedelta(days=days) in ready:
        days += 1
    return days


def upcoming(today: date) -> list[tuple[date, Puzzle | None]]:
    end = today + timedelta(days=CALENDAR_DAYS)
    puzzles = db.session.scalars(
        select(Puzzle).where(Puzzle.publish_date >= today, Puzzle.publish_date < end)
    )
    by_day = {puzzle.publish_date: puzzle for puzzle in puzzles}
    days = [today + timedelta(days=offset) for offset in range(CALENDAR_DAYS)]
    return [(day, by_day.get(day)) for day in days]


def _date_taken(day: date, puzzle: Puzzle | None) -> bool:
    query = select(Puzzle.id).where(Puzzle.publish_date == day)
    if puzzle is not None:
        query = query.where(Puzzle.id != puzzle.id)
    return db.session.scalar(query) is not None


def save_puzzle(form, puzzle: Puzzle | None, today: date) -> Puzzle | None:
    """Check cross-field rules, then create or update the puzzle."""
    errors = {}

    answer = turkish_upper(form.answer.data.strip())
    expected = answer_length(form.enumeration.data)
    actual = len(normalize_answer(answer))
    if actual != expected:
        errors["answer"] = f"Cevap {actual} harf, harf sayısı {expected} diyor."

    hints = [line.strip() for line in (form.hints.data or "").splitlines() if line.strip()]
    definition = (form.definition.data or "").strip() or None
    if definition is None and not hints:
        errors["hints"] = "Tanımı olmayan bulmacaya en az bir ipucu yaz."
    if definition and turkish_upper(definition) not in turkish_upper(form.clue.data):
        errors["definition"] = "Tanım ipucunun içinde geçmiyor."

    day = None
    if form.kind.data == "daily":
        day = next_free_day(today) if form.next_free_day.data else form.publish_date.data
        current = puzzle.publish_date if puzzle else None
        if day is None and form.status.data == "ready":
            errors["publish_date"] = "Hazır günlük bulmacanın tarihi olmalı."
        elif day is not None and day != current:
            if day < today:
                errors["publish_date"] = "Geçmiş bir tarihe bulmaca konamaz."
            elif _date_taken(day, puzzle):
                errors["publish_date"] = "Bu tarihte başka bir bulmaca var."

    if errors:
        for name, message in errors.items():
            getattr(form, name).errors.append(message)
        return None

    if puzzle is None:
        puzzle = Puzzle()
        db.session.add(puzzle)

    puzzle.kind = form.kind.data
    puzzle.status = form.status.data
    puzzle.clue = form.clue.data.strip()
    puzzle.definition = definition
    puzzle.answer = answer
    puzzle.enumeration = form.enumeration.data.strip()
    puzzle.hints = hints
    puzzle.explanation = form.explanation.data.strip()
    puzzle.technique = form.technique.data
    puzzle.difficulty = form.difficulty.data
    puzzle.publish_date = day

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        form.publish_date.errors.append("Bu tarihte başka bir bulmaca var.")
        return None
    return puzzle