from datetime import UTC, datetime, timedelta

import pytest

from muamma.community import MIN_SOLVERS, community_line, community_stats
from muamma.extensions import db
from muamma.models import Play, Player
from tests.helpers import TODAY, add_puzzle


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def add_solvers(puzzle, guesses, seconds, status="solved"):
    """One finished play per entry, each by its own player."""
    start = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
    for count, taken in zip(guesses, seconds):
        player = Player()
        db.session.add(player)
        db.session.flush()
        db.session.add(
            Play(
                player_id=player.id,
                puzzle_id=puzzle.id,
                status=status,
                guess_count=count,
                started_at=start,
                finished_at=start + timedelta(seconds=taken),
            )
        )
    db.session.commit()


def test_no_line_below_the_threshold(client):
    puzzle = add_puzzle()
    add_solvers(puzzle, [2] * (MIN_SOLVERS - 1), [200] * (MIN_SOLVERS - 1))

    assert community_stats(puzzle) is None
    assert community_line(puzzle, TODAY) is None


def test_line_appears_at_the_threshold(client):
    puzzle = add_puzzle()
    add_solvers(puzzle, [2] * MIN_SOLVERS, [200] * MIN_SOLVERS)

    assert community_line(puzzle, TODAY).startswith("Bugün çözenler")


def test_mean_guesses_use_a_comma(client):
    puzzle = add_puzzle()
    guesses = [2] * 14 + [3] * 6  # mean 2.3
    add_solvers(puzzle, guesses, [252] * MIN_SOLVERS)

    assert "ortalama 2,3 tahminde" in community_line(puzzle, TODAY)


def test_median_ignores_one_huge_time(client):
    puzzle = add_puzzle()
    seconds = [252] * (MIN_SOLVERS - 1) + [40_000]
    add_solvers(puzzle, [2] * MIN_SOLVERS, seconds)

    assert "genelde 4 dk 12 sn'de çözdü" in community_line(puzzle, TODAY)


def test_only_solved_plays_count(client):
    puzzle = add_puzzle()
    add_solvers(puzzle, [2] * MIN_SOLVERS, [252] * MIN_SOLVERS, status="revealed")
    add_solvers(puzzle, [9] * 5, [9_000] * 5, status="in_progress")

    assert community_stats(puzzle) is None


def test_archive_line_names_the_puzzle(client):
    puzzle = add_puzzle(publish_date=TODAY - timedelta(days=1))
    add_solvers(puzzle, [2] * MIN_SOLVERS, [45] * MIN_SOLVERS)

    line = community_line(puzzle, TODAY)
    assert line.startswith("Bu muammayı çözenler")
    assert "genelde 45 sn'de çözdü" in line


def test_finished_page_and_guess_carry_the_line(client):
    puzzle = add_puzzle()
    add_solvers(puzzle, [2] * MIN_SOLVERS, [252] * MIN_SOLVERS)

    data = client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": "arı"}).get_json()
    assert "ortalama" in data["community"]

    html = client.get("/").get_data(as_text=True)
    assert 'class="result-community"' in html
    assert "ortalama" in html
