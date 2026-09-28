from datetime import timedelta

import pytest
from sqlalchemy import func, select

from muamma.extensions import db
from muamma.models import Event, Play, Player
from tests.helpers import TODAY, add_puzzle


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)
    
def guess(client, puzzle, value):
    return client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": value})


def count(model):
    return db.session.scalar(select(func.count()).select_from(model))


def the_player():
    return db.session.scalar(select(Player))


def test_page_view_does_not_create_player(client):
    add_puzzle()
    client.get("/")
    assert count(Player) == 0


def test_guesses_are_recorded(client):
    puzzle = add_puzzle()
    guess(client, puzzle, "ark")
    guess(client, puzzle, "arı")

    play = db.session.scalar(select(Play))
    assert count(Player) == 1
    assert play.guess_count == 2
    assert play.status == "solved"
    assert count(Event) == 3


def test_wrong_length_is_not_recorded(client):
    puzzle = add_puzzle()
    guess(client, puzzle, "arıza")
    assert count(Player) == 0


def test_solving_todays_puzzle_starts_streak(client):
    puzzle = add_puzzle()
    data = guess(client, puzzle, "arı").get_json()
    assert data["streak"] == 1
    assert the_player().max_streak == 1


def test_streak_continues_on_consecutive_days(client, monkeypatch):
    yesterday = TODAY - timedelta(days=1)
    first = add_puzzle(publish_date=yesterday)
    second = add_puzzle(publish_date=TODAY, answer="ÇAM", clue="Kaçamakta gizlenen ağaç")

    monkeypatch.setattr("muamma.clock.today", lambda: yesterday)
    guess(client, first, "arı")
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)
    data = guess(client, second, "çam").get_json()

    assert data["streak"] == 2


def test_archive_solve_does_not_count_for_streak(client):
    puzzle = add_puzzle(publish_date=TODAY - timedelta(days=3))
    data = guess(client, puzzle, "arı").get_json()

    assert data["streak"] == 0
    assert db.session.scalar(select(Play)).counts_for_streak is False


def test_finished_puzzle_rejects_guesses(client):
    puzzle = add_puzzle()
    guess(client, puzzle, "arı")
    response = guess(client, puzzle, "arı")
    assert response.status_code == 409


def test_page_remembers_solved_puzzle(client):
    puzzle = add_puzzle()
    guess(client, puzzle, "arı")
    html = client.get("/").get_data(as_text=True)
    assert "k-ARI-nca" in html
    assert 'class="streak-count">1<' in html