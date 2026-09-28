from datetime import date

import pytest

from muamma.models import Play, Puzzle
from muamma.share import share_text
from tests.helpers import TODAY, add_puzzle

URL = "https://muamma.example/"


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def daily():
    return Puzzle(kind="daily", publish_date=date(2026, 10, 10))


def finished(status="solved", guesses=2, hints=0, letters=0):
    return Play(status=status, guess_count=guesses, hints_used=hints, letters_revealed=letters)


def guess(client, puzzle, value):
    return client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": value}).get_json()


def test_unassisted_solve():
    assert share_text(daily(), finished(), 3, URL).splitlines() == [
        "Muamma · 10.10.2026",
        "✅ 2. tahminde çözdüm",
        "🧠 Yardımsız",
        "🔥 Seri: 3",
        URL,
    ]


def test_assisted_solve_lists_help():
    text = share_text(daily(), finished(hints=1, letters=2), 0, URL)
    assert "💡 1 ipucu · 🔤 2 harf" in text
    assert "Seri" not in text


def test_revealed_answer():
    assert "❌ Cevaba baktım" in share_text(daily(), finished(status="revealed"), 0, URL)


def test_practice_is_not_shared():
    assert share_text(Puzzle(kind="practice"), finished(), 0, URL) is None


def test_daily_solution_has_share_and_countdown(client):
    puzzle = add_puzzle()
    data = guess(client, puzzle, "arı")
    assert data["share"].startswith("Muamma · 10.10.2026")
    assert "ARI" not in data["share"]
    assert 0 < data["next_in"] <= 86400


def test_practice_solution_has_neither(client):
    puzzle = add_puzzle(kind="practice", publish_date=None)
    data = guess(client, puzzle, "arı")
    assert data["share"] is None
    assert data["next_in"] is None


def test_new_visitor_sees_intro(client):
    puzzle = add_puzzle()
    assert "ilk kez mi" in client.get("/").get_data(as_text=True)
    guess(client, puzzle, "ark")
    assert "ilk kez mi" not in client.get("/").get_data(as_text=True)


def test_how_to_play_page(client):
    html = client.get("/nasil-oynanir").get_data(as_text=True)
    assert "Anagram" in html
    assert "Nasıl oynanır – Muamma" in html