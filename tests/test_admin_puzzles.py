from datetime import timedelta

import pytest
from sqlalchemy import select

from muamma.extensions import db
from muamma.models import Admin, Play, Player, Puzzle
from muamma.security import hash_password
from tests.helpers import TODAY, add_puzzle


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


@pytest.fixture
def admin_client(client):
    password = "correct horse battery"
    db.session.add(Admin(email="admin@example.com", password_hash=hash_password(password)))
    db.session.commit()
    client.post("/admin/login", data={"email": "admin@example.com", "password": password})
    return client


def form_data(**overrides):
    data = {
        "kind": "daily",
        "status": "ready",
        "clue": "Karıncanın içinde saklanan bal yapıcı",
        "definition": "bal yapıcı",
        "answer": "arı",
        "enumeration": "3",
        "hints": "",
        "explanation": "k-ARI-nca",
        "technique": "hidden",
        "difficulty": "1",
        "publish_date": (TODAY + timedelta(days=2)).isoformat(),
    }
    data.update(overrides)
    return data


def create(client, **overrides):
    return client.post("/admin/puzzles/new", data=form_data(**overrides))


def all_puzzles():
    return db.session.scalars(select(Puzzle).order_by(Puzzle.id)).all()


def test_puzzle_pages_require_login(client):
    assert client.get("/admin/puzzles").status_code == 302


def test_create_daily_puzzle(admin_client):
    assert create(admin_client).status_code == 302
    [puzzle] = all_puzzles()
    assert puzzle.answer == "ARI"
    assert puzzle.publish_date == TODAY + timedelta(days=2)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"answer": "arıza"}, "Cevap 5 harf"),
        ({"definition": "", "hints": ""}, "en az bir ipucu"),
        ({"definition": "uçan böcek"}, "ipucunun içinde geçmiyor"),
        ({"publish_date": (TODAY - timedelta(days=1)).isoformat()}, "Geçmiş bir tarihe"),
    ],
)
def test_invalid_puzzle_is_rejected(admin_client, overrides, message):
    html = create(admin_client, **overrides).get_data(as_text=True)
    assert message in html
    assert all_puzzles() == []


def test_taken_date_is_rejected(admin_client):
    add_puzzle(publish_date=TODAY + timedelta(days=2))
    html = create(admin_client).get_data(as_text=True)
    assert "başka bir bulmaca var" in html


def test_next_free_day_skips_taken_dates(admin_client):
    add_puzzle(publish_date=TODAY)
    add_puzzle(publish_date=TODAY + timedelta(days=1), answer="ÇAM")
    create(admin_client, publish_date="", next_free_day="y")
    assert all_puzzles()[-1].publish_date == TODAY + timedelta(days=2)


def test_practice_puzzle_has_no_date(admin_client):
    create(admin_client, kind="practice")
    assert all_puzzles()[0].publish_date is None


def test_published_puzzle_keeps_locked_fields(admin_client):
    puzzle = add_puzzle(publish_date=TODAY)
    admin_client.post(
        f"/admin/puzzles/{puzzle.id}",
        data=form_data(
            answer="xyz",
            clue="Karıncanın içinde saklanan bal yapıcı!",
            publish_date="",
        ),
    )
    db.session.refresh(puzzle)
    assert puzzle.answer == "ARI"
    assert puzzle.publish_date == TODAY
    assert puzzle.clue.endswith("!")


def test_played_puzzle_cannot_be_deleted(admin_client):
    puzzle = add_puzzle(kind="practice", publish_date=None)
    db.session.add(
        Play(
            player=Player(current_streak=0, max_streak=0),
            puzzle=puzzle,
            status="in_progress",
            guess_count=0,
            hints_used=0,
            letters_revealed=0,
            counts_for_streak=False,
        )
    )
    db.session.commit()
    admin_client.post(f"/admin/puzzles/{puzzle.id}/delete")
    assert len(all_puzzles()) == 1


def test_unplayed_draft_can_be_deleted(admin_client):
    puzzle = add_puzzle(status="draft", publish_date=None)
    admin_client.post(f"/admin/puzzles/{puzzle.id}/delete")
    assert all_puzzles() == []


def test_dashboard_counts_consecutive_stock(admin_client):
    for offset, answer in [(0, "ARI"), (1, "BAL"), (3, "KOY")]:
        add_puzzle(publish_date=TODAY + timedelta(days=offset), answer=answer)
    html = admin_client.get("/admin/").get_data(as_text=True)
    assert "2 gün" in html