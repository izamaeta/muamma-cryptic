from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from muamma.extensions import db
from muamma.models import Player, Puzzle


def make_puzzle(**overrides):
    fields = {
        "kind": "daily",
        "status": "ready",
        "clue": "Karıncanın içinde saklanan bal yapıcı",
        "definition": "bal yapıcı",
        "answer": "ARI",
        "enumeration": "3",
        "explanation": "k-ARI-nca",
        "technique": "hidden",
        "publish_date": date(2026, 10, 1),
    }
    fields.update(overrides)
    return Puzzle(**fields)


def test_daily_puzzle_dates_are_unique(app):
    db.session.add_all([make_puzzle(), make_puzzle(answer="KELAM")])
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_ready_daily_puzzle_requires_date(app):
    db.session.add(make_puzzle(publish_date=None))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_draft_daily_puzzle_may_have_no_date(app):
    db.session.add(make_puzzle(status="draft", publish_date=None))
    db.session.commit()


def test_practice_puzzle_cannot_have_date(app):
    db.session.add(make_puzzle(kind="practice"))
    with pytest.raises(IntegrityError):
        db.session.commit()


@pytest.mark.parametrize(
    ("last", "expected"),
    [
        (None, 0),
        (date(2026, 10, 10), 5),
        (date(2026, 10, 9), 5),
        (date(2026, 10, 8), 0),
    ],
)
def test_displayed_streak(last, expected):
    player = Player(current_streak=5, last_streak_date=last)
    assert player.displayed_streak(date(2026, 10, 10)) == expected