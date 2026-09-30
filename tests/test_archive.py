from datetime import timedelta

import pytest

from tests.helpers import TODAY, add_puzzle


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def past(days, **fields):
    return add_puzzle(publish_date=TODAY - timedelta(days=days), **fields)


def page(puzzle):
    return f"/bulmaca/{puzzle.publish_date.isoformat()}"


def test_archive_lists_past_puzzles_newest_first(client):
    past(1)
    past(2)
    past(3)

    html = client.get("/arsiv").get_data(as_text=True)
    assert html.index("9 Ekim 2026") < html.index("8 Ekim 2026") < html.index("7 Ekim 2026")


def test_archive_hides_today_future_and_drafts(client):
    add_puzzle()
    add_puzzle(publish_date=TODAY + timedelta(days=2))
    past(5, status="draft")
    past(1)

    html = client.get("/arsiv").get_data(as_text=True)
    assert "9 Ekim 2026" in html
    assert "12 Ekim 2026" not in html
    assert "5 Ekim 2026" not in html


def test_archive_shows_play_labels(client):
    solved = past(1)
    revealed = past(2)
    past(3)

    client.post(f"/api/puzzles/{solved.id}/guess", json={"guess": "arı"})
    client.post(f"/api/puzzles/{revealed.id}/reveal")

    html = client.get("/arsiv").get_data(as_text=True)
    assert html.count("Çözüldü") == 1
    assert html.count("Cevaba bakıldı") == 1


def test_archive_without_player_has_no_labels(client):
    past(1)
    html = client.get("/arsiv").get_data(as_text=True)
    assert "Çözüldü" not in html
    assert "Cevaba bakıldı" not in html


def test_archive_puzzle_is_playable_and_hides_the_answer(client):
    puzzle = past(1)
    html = client.get(page(puzzle)).get_data(as_text=True)

    assert "Karıncanın içinde saklanan bal yapıcı" in html
    assert 'data-state="sealed"' in html
    assert "k-ARI-nca" not in html
    assert "9 Ekim 2026" in html


def test_archive_puzzle_reopens_as_opened(client):
    puzzle = past(1)
    client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": "arı"})

    html = client.get(page(puzzle)).get_data(as_text=True)
    assert 'data-state="opened"' in html
    assert "k-ARI-nca" in html


@pytest.mark.parametrize(
    "raw",
    ["20261009", "2026-10", "2026-10-9", "2026-W41-5", "0000-00-00", "bugun"],
)
def test_only_plain_iso_dates_are_accepted(client, raw):
    past(1)
    assert client.get(f"/bulmaca/{raw}").status_code == 404


def test_today_redirects_to_the_home_page(client):
    add_puzzle()
    response = client.get("/bulmaca/2026-10-10")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_future_dates_are_404(client):
    puzzle = add_puzzle(publish_date=TODAY + timedelta(days=2))
    assert client.get(page(puzzle)).status_code == 404


def test_draft_puzzles_are_404(client):
    puzzle = past(1, status="draft")
    assert client.get(page(puzzle)).status_code == 404


def test_archive_puzzle_links_to_its_neighbours(client):
    past(1)
    middle = past(2)
    past(3)

    html = client.get(page(middle)).get_data(as_text=True)
    assert 'href="/bulmaca/2026-10-07"' in html
    assert 'href="/bulmaca/2026-10-09"' in html


def test_next_link_points_to_today(client):
    add_puzzle()
    puzzle = past(1)

    html = client.get(page(puzzle)).get_data(as_text=True)
    assert "Bugünün bulmacası" in html
    assert 'href="/bulmaca/2026-10-10"' not in html


def test_sitemap_lists_archive_puzzles_with_lastmod(client):
    puzzle = past(1)
    location = f"<loc>https://muamma.test/bulmaca/{puzzle.publish_date.isoformat()}</loc>"
    lastmod = max(puzzle.publish_date, puzzle.updated_at.date()).isoformat()

    body = client.get("/sitemap.xml").get_data(as_text=True)
    assert f"{location}<lastmod>{lastmod}</lastmod>" in body


def test_sitemap_skips_today_and_future_puzzles(client):
    add_puzzle()
    add_puzzle(publish_date=TODAY + timedelta(days=2))

    body = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/bulmaca/2026-10-10" not in body
    assert "/bulmaca/2026-10-12" not in body


def test_archive_solve_leaves_the_streak_alone(client):
    puzzle = past(1)
    client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": "arı"})

    html = client.get("/arsiv").get_data(as_text=True)
    assert '<span class="streak-count">0</span>' in html
