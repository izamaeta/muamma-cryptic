from datetime import timedelta

import pytest
from sqlalchemy import select

from muamma.extensions import db
from muamma.models import Play, Player
from tests.helpers import TODAY, add_puzzle

EXTRA_HINT = "İçinde saklı bir kelime var."


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def post(client, puzzle, action, **body):
    return client.post(f"/api/puzzles/{puzzle.id}/{action}", json=body)


def test_first_hint_is_definition(client):
    puzzle = add_puzzle(hints=[EXTRA_HINT])
    first = post(client, puzzle, "hint").get_json()
    second = post(client, puzzle, "hint").get_json()

    assert first["text"] == "Tanım: bal yapıcı"
    assert first["remaining"] == 1
    assert "highlight" in first
    assert second == {"text": EXTRA_HINT, "remaining": 0}
    assert post(client, puzzle, "hint").status_code == 409
    

def test_letters_are_revealed_in_order(client):
    puzzle = add_puzzle()
    assert post(client, puzzle, "letter").get_json()["pattern"] == "A__"
    assert post(client, puzzle, "letter").get_json()["pattern"] == "AR_"
    assert post(client, puzzle, "letter").status_code == 409


def test_pattern_keeps_word_breaks(client):
    puzzle = add_puzzle(answer="GÖK YÜZÜ", enumeration="3,4")
    assert post(client, puzzle, "letter").get_json()["pattern"] == "G__ ____"


def test_reveal_ends_play_and_resets_streak(client):
    puzzle = add_puzzle()
    post(client, puzzle, "hint")
    player = db.session.scalar(select(Player))
    player.current_streak = 4
    player.last_streak_date = TODAY - timedelta(days=1)
    db.session.commit()

    data = post(client, puzzle, "reveal").get_json()

    assert data["answer"] == "ARI"
    assert data["streak"] == 0
    assert db.session.scalar(select(Play)).status == "revealed"
    assert post(client, puzzle, "guess", guess="arı").status_code == 409


def test_progress_survives_reload(client):
    puzzle = add_puzzle(hints=[EXTRA_HINT])
    post(client, puzzle, "hint")
    post(client, puzzle, "letter")
    html = client.get("/").get_data(as_text=True)

    assert "Tanım: bal yapıcı" in html
    assert "A__" in html
    assert EXTRA_HINT not in html


def test_practice_redirects_to_unplayed_puzzle(client):
    puzzle = add_puzzle(kind="practice", publish_date=None)
    response = client.get("/tadimlik")
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/tadimlik/{puzzle.id}")


def test_practice_skips_finished_puzzles(client):
    puzzle = add_puzzle(kind="practice", publish_date=None)
    post(client, puzzle, "guess", guess="arı")
    html = client.get("/tadimlik").get_data(as_text=True)
    assert "Hepsini çözdün" in html


def test_daily_puzzle_is_not_served_as_practice(client):
    puzzle = add_puzzle()
    assert client.get(f"/tadimlik/{puzzle.id}").status_code == 404


def test_stats_page(client):
    puzzle = add_puzzle()
    post(client, puzzle, "guess", guess="arı")
    html = client.get("/istatistik").get_data(as_text=True)
    assert "%100" in html


def test_stats_page_without_player(client):
    html = client.get("/istatistik").get_data(as_text=True)
    assert "Henüz bir bulmaca oynamadın" in html

    
def test_clue_without_definition_starts_with_own_hints(client):
    puzzle = add_puzzle(definition=None, hints=[EXTRA_HINT])
    assert post(client, puzzle, "hint").get_json() == {"text": EXTRA_HINT, "remaining": 0}