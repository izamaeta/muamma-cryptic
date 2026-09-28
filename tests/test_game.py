from datetime import date

import pytest

from muamma.extensions import db
from muamma.models import Puzzle

TODAY = date(2026, 10, 10)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def add_puzzle(**overrides):
    fields = {
        "kind": "daily",
        "status": "ready",
        "clue": "Karıncanın içinde saklanan bal yapıcı",
        "definition": "bal yapıcı",
        "answer": "ARI",
        "enumeration": "3",
        "explanation": "k-ARI-nca",
        "technique": "hidden",
        "publish_date": TODAY,
    }
    fields.update(overrides)
    puzzle = Puzzle(**fields)
    db.session.add(puzzle)
    db.session.commit()
    return puzzle


def guess(client, puzzle, value):
    return client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": value})


def test_index_shows_clue_without_solution(client):
    add_puzzle()
    html = client.get("/").get_data(as_text=True)
    assert "Karıncanın içinde saklanan bal yapıcı" in html
    assert "k-ARI-nca" not in html


def test_index_without_puzzle(client):
    html = client.get("/").get_data(as_text=True)
    assert "hazırlanıyor" in html


def test_correct_guess_returns_solution(client):
    puzzle = add_puzzle()
    data = guess(client, puzzle, "arı").get_json()
    assert data["correct"] is True
    assert data["explanation"] == "k-ARI-nca"


def test_wrong_guess(client):
    puzzle = add_puzzle()
    data = guess(client, puzzle, "ark").get_json()
    assert data == {"correct": False}


def test_wrong_length(client):
    puzzle = add_puzzle()
    response = guess(client, puzzle, "arıza")
    assert response.status_code == 400
    assert response.get_json()["error"] == "wrong_length"


def test_future_puzzle_is_hidden(client):
    puzzle = add_puzzle(publish_date=date(2026, 10, 11))
    assert guess(client, puzzle, "arı").status_code == 404
    assert "hazırlanıyor" in client.get("/").get_data(as_text=True)


def test_draft_puzzle_is_hidden(client):
    puzzle = add_puzzle(status="draft")
    assert guess(client, puzzle, "arı").status_code == 404


def test_invalid_payload(client):
    puzzle = add_puzzle()
    response = client.post(f"/api/puzzles/{puzzle.id}/guess", data="not json")
    assert response.status_code == 400