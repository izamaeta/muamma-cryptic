from datetime import date, timedelta

import pytest

from tests.helpers import TODAY, add_puzzle

SUNDAY = date(2026, 10, 11)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def test_sealed_page_shows_envelope_layers_seal_and_no_old_partials(client):
    add_puzzle()
    html = client.get("/").get_data(as_text=True)

    for layer in (
        "env-shadow",
        "env-pocket",
        "env-flap-front",
        "env-flap-shadow",
        "gs-whole",
        "seal-shadow",
    ):
        assert layer in html, layer
    assert '<p class="env-face-title">Bugünün muamması</p>' in html
    assert 'class="env-layer gs-cracked"' in html  # present, hidden
    assert "gs-piece-1" in html

    for old in ("band-wash", "seal-cap", "seal-label", "seal-title", "MÜHÜRLÜ"):
        assert old not in html


def test_finished_page_shows_letter_text_and_no_seal(client):
    puzzle = add_puzzle()
    client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": "arı"})

    html = client.get("/").get_data(as_text=True)
    assert "Mühür kırıldı" in html
    assert "Muamma çözüldü!" in html
    for seal_asset in ("gs-whole", "gs-cracked", "gs-piece", "seal-shadow"):
        assert seal_asset not in html
    assert 'data-state="opened"' in html


def test_revealed_page_shows_its_own_letter_text(client):
    puzzle = add_puzzle()
    client.post(f"/api/puzzles/{puzzle.id}/reveal")

    html = client.get("/").get_data(as_text=True)
    assert "Mühür açıldı" in html
    assert "Cevaba bakıldı" in html
    assert "gs-whole" not in html


@pytest.mark.parametrize(
    ("path_fn", "title"),
    [
        (lambda: "/", "Bugünün muamması"),
        (lambda: "/tadimlik/", "Tadımlık"),
    ],
)
def test_sealed_titles_per_section(client, path_fn, title):
    if title == "Tadımlık":
        puzzle = add_puzzle(kind="practice", publish_date=None)
        path = f"/tadimlik/{puzzle.id}"
    else:
        add_puzzle()
        path = path_fn()

    html = client.get(path).get_data(as_text=True)
    assert f'<p class="env-face-title">{title}</p>' in html


def test_sunday_title_on_the_daily_band(client, monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: SUNDAY)
    add_puzzle(publish_date=SUNDAY, difficulty=3)

    html = client.get("/").get_data(as_text=True)
    assert '<p class="env-face-title">Haftanın çetin muamması</p>' in html


def test_archive_title_on_a_past_puzzle(client):
    puzzle = add_puzzle(publish_date=TODAY - timedelta(days=1))

    html = client.get(f"/bulmaca/{puzzle.publish_date.isoformat()}").get_data(as_text=True)
    assert '<p class="env-face-title">Arşiv muamması</p>' in html


def test_the_seal_mount_is_not_rendered_for_an_already_finished_reload(client):
    puzzle = add_puzzle()
    client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": "arı"})

    html = client.get("/").get_data(as_text=True)
    assert "env-seal-mount" not in html
