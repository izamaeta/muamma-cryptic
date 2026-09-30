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


def shown(pattern):
    """Letters the pattern reveals, ignoring where they fall."""
    return [ch for ch in pattern if ch not in "_ "]


def test_first_hint_is_definition(client):
    puzzle = add_puzzle(hints=[EXTRA_HINT])
    first = post(client, puzzle, "hint").get_json()
    second = post(client, puzzle, "hint").get_json()

    assert first["text"] == "Tanım: bal yapıcı"
    assert first["remaining"] == 1
    assert "highlight" in first
    assert second == {"text": EXTRA_HINT, "remaining": 0}
    assert post(client, puzzle, "hint").status_code == 409
    

def test_letters_open_one_at_a_time(client):
    puzzle = add_puzzle()

    first = post(client, puzzle, "letter").get_json()["pattern"]
    assert len(shown(first)) == 1
    assert first.count("_") == 2

    second = post(client, puzzle, "letter").get_json()["pattern"]
    assert len(shown(second)) == 2
    assert second.count("_") == 1

    assert post(client, puzzle, "letter").status_code == 409


def test_pattern_keeps_word_breaks(client):
    puzzle = add_puzzle(answer="GÖK YÜZÜ", enumeration="3,4")
    pattern = post(client, puzzle, "letter").get_json()["pattern"]

    words = pattern.split(" ")
    assert [len(word) for word in words] == [3, 4]
    assert len(shown(pattern)) == 1


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
    pattern = post(client, puzzle, "letter").get_json()["pattern"]
    html = client.get("/").get_data(as_text=True)

    assert "Tanım: bal yapıcı" in html
    assert pattern in html
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


def test_stats_endpoint_counts_a_solve(client):
    puzzle = add_puzzle()
    post(client, puzzle, "guess", guess="arı")

    data = client.get("/api/me/stats").get_json()
    assert data["daily_played"] == 1
    assert data["daily_solved"] == 1
    assert data["solve_rate"] == 100
    assert data["current_streak"] == 1


def test_stats_endpoint_without_a_player(client):
    data = client.get("/api/me/stats").get_json()
    assert data == {
        "daily_played": 0,
        "daily_solved": 0,
        "solve_rate": 0,
        "current_streak": 0,
        "max_streak": 0,
        "practice_solved": 0,
    }

    
def test_clue_without_definition_starts_with_own_hints(client):
    puzzle = add_puzzle(definition=None, hints=[EXTRA_HINT])
    assert post(client, puzzle, "hint").get_json() == {"text": EXTRA_HINT, "remaining": 0}

def open_all_letters(client, puzzle):
    """Keep opening letters until the API refuses."""
    patterns = []
    while True:
        response = post(client, puzzle, "letter")
        if response.status_code == 409:
            return patterns
        patterns.append(response.get_json()["pattern"])


def test_reveal_order_is_stable_for_a_player(client):
    puzzle = add_puzzle(answer="GÖK YÜZÜ", enumeration="3,4")

    first = post(client, puzzle, "letter").get_json()["pattern"]
    assert first in client.get("/").get_data(as_text=True)

    second = post(client, puzzle, "letter").get_json()["pattern"]
    assert shown(first)[0] in shown(second)
    assert second in client.get("/").get_data(as_text=True)


def test_players_can_get_different_letters(app):
    puzzle = add_puzzle(answer="GÖK YÜZÜ", enumeration="3,4")
    orders = set()

    for _ in range(12):
        client = app.test_client()
        orders.add(post(client, puzzle, "letter").get_json()["position"])

    assert len(orders) > 1


def test_the_last_letter_never_opens(client):
    puzzle = add_puzzle(answer="GÖK YÜZÜ", enumeration="3,4")
    patterns = open_all_letters(client, puzzle)

    assert len(patterns) == 6
    assert patterns[-1].endswith("_")
    assert "_" in patterns[-1]


def test_revealed_position_holds_that_letter(client):
    puzzle = add_puzzle(answer="GÖK YÜZÜ", enumeration="3,4")
    data = post(client, puzzle, "letter").get_json()

    letters = data["pattern"].replace(" ", "")
    assert letters[data["position"]] == "GÖKYÜZÜ"[data["position"]]
    assert letters.count("_") == 6
