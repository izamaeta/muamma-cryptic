from datetime import date, timedelta

import pytest
from sqlalchemy import select

from muamma.admin.services import sunday_gaps, sunday_warning
from muamma.extensions import db
from muamma.models import Admin, Puzzle
from muamma.security import hash_password
from tests.helpers import add_puzzle

# 11 October 2026 is a Sunday
SUNDAY = date(2026, 10, 11)
MONDAY = SUNDAY + timedelta(days=1)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: SUNDAY)


@pytest.fixture
def admin_client(client):
    password = "correct horse battery"
    db.session.add(Admin(email="admin@example.com", password_hash=hash_password(password)))
    db.session.commit()
    client.post("/admin/login", data={"email": "admin@example.com", "password": password})
    return client


def test_sunday_puzzle_gets_the_hard_title(client):
    add_puzzle(publish_date=SUNDAY, difficulty=3)
    html = client.get("/").get_data(as_text=True)
    assert "Haftanın çetin muamması" in html
    assert "MÜHÜRLÜ" in html


def test_other_days_keep_their_title(client):
    add_puzzle(publish_date=SUNDAY)  # today, so the archive page needs another day
    add_puzzle(publish_date=SUNDAY - timedelta(days=2), answer="ÇAM", clue="Kaçamakta gizlenen ağaç", definition="ağaç")

    html = client.get(f"/bulmaca/{(SUNDAY - timedelta(days=2)).isoformat()}").get_data(as_text=True)
    assert "Arşiv muamması" in html
    assert "Haftanın çetin muamması" not in html


def test_archive_sunday_keeps_the_hard_title(client, monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: MONDAY)
    add_puzzle(publish_date=SUNDAY, difficulty=3)

    html = client.get(f"/bulmaca/{SUNDAY.isoformat()}").get_data(as_text=True)
    assert "Haftanın çetin muamması" in html


def test_practice_is_never_a_sunday_puzzle(client):
    puzzle = add_puzzle(kind="practice", publish_date=None)
    html = client.get(f"/tadimlik/{puzzle.id}").get_data(as_text=True)
    assert "Haftanın çetin muamması" not in html


def test_empty_sunday_is_reported(client):
    assert SUNDAY in sunday_gaps(SUNDAY)


def test_easy_sunday_is_reported(client):
    add_puzzle(publish_date=SUNDAY, difficulty=2)
    assert SUNDAY in sunday_gaps(SUNDAY)


def test_hard_sunday_is_not_reported(client):
    add_puzzle(publish_date=SUNDAY, difficulty=3)
    assert SUNDAY not in sunday_gaps(SUNDAY)


def test_weekdays_are_never_reported(client):
    assert all(day.weekday() == 6 for day in sunday_gaps(SUNDAY))


def test_warning_text_only_for_easy_sundays(client):
    assert sunday_warning(add_puzzle(publish_date=SUNDAY, difficulty=2)) is not None
    assert sunday_warning(add_puzzle(publish_date=MONDAY, difficulty=1)) is None


def test_easy_sunday_is_still_saved(admin_client):
    response = admin_client.post(
        "/admin/puzzles/new",
        data={
            "kind": "daily",
            "status": "draft",
            "clue": "Karıncanın içinde saklanan bal yapıcı",
            "definition": "bal yapıcı",
            "answer": "arı",
            "enumeration": "3",
            "hints": "",
            "explanation": "k-ARI-nca",
            "technique": "hidden",
            "difficulty": "1",
            "publish_date": SUNDAY.isoformat(),
        },
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)

    assert "Bulmaca kaydedildi." in html
    assert "haftanın çetin muamması olmalı" in html
    assert db.session.scalar(select(Puzzle).where(Puzzle.publish_date == SUNDAY)) is not None


def test_dashboard_marks_sundays_and_warns(admin_client):
    html = admin_client.get("/admin/").get_data(as_text=True)

    assert "haftanın çetin muamması olmalı" in html
    assert SUNDAY.strftime("%d.%m.%Y") in html
    assert ">pazar</span>" in html


def test_dashboard_stops_warning_once_sunday_is_hard(admin_client):
    for offset in range(14):
        day = SUNDAY + timedelta(days=offset)
        if day.weekday() == 6:
            add_puzzle(
                publish_date=day,
                difficulty=3,
                answer="ÇAM",
                clue="Kaçamakta gizlenen ağaç",
                definition="ağaç",
            )

    html = admin_client.get("/admin/").get_data(as_text=True)
    assert "haftanın çetin muamması olmalı" not in html
