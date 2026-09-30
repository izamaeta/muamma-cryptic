import pytest

from tests.helpers import TODAY, add_puzzle


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def guess(client, puzzle, value):
    return client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": value})


def test_fonts_are_loaded_before_the_stylesheet(client):
    html = client.get("/").get_data(as_text=True)
    assert html.index("css/fonts.css") < html.index("css/style.css")


def test_theme_script_is_in_the_head(client):
    html = client.get("/").get_data(as_text=True)
    head = html[: html.index("</head>")]
    assert "js/theme.js" in head
    assert 'class="theme-toggle"' not in head


def test_favicons_are_png(client):
    html = client.get("/").get_data(as_text=True)
    assert 'type="image/png" sizes="32x32"' in html
    assert 'rel="apple-touch-icon"' in html
    assert "favicon.svg" not in html


def test_header_shows_the_logo(client):
    html = client.get("/").get_data(as_text=True)
    assert 'alt="Muamma"' in html
    assert "img/logo/logo-192.png" in html


def test_band_shows_the_date_and_sealed_state(client):
    add_puzzle()
    html = client.get("/").get_data(as_text=True)
    assert 'data-state="sealed"' in html
    assert "10 Ekim 2026" in html
    assert "MÜHÜRLÜ" in html
    assert 'class="seal seal-whole"' in html


def test_solved_puzzle_reopens_as_opened(client):
    puzzle = add_puzzle()
    guess(client, puzzle, "arı")

    html = client.get("/").get_data(as_text=True)
    assert 'data-state="opened"' in html
    assert "Mühür kırıldı" in html
    assert "Muamma çözüldü!" in html


def test_revealed_puzzle_reopens_as_opened(client):
    puzzle = add_puzzle()
    client.post(f"/api/puzzles/{puzzle.id}/reveal")

    html = client.get("/").get_data(as_text=True)
    assert 'data-state="opened"' in html
    assert "Mühür açıldı" in html


def test_unfinished_puzzle_stays_sealed_on_reload(client):
    puzzle = add_puzzle()
    guess(client, puzzle, "çam")

    html = client.get("/").get_data(as_text=True)
    assert 'data-state="sealed"' in html


def test_pages_without_a_band_are_not_tall(client):
    html = client.get("/gizlilik").get_data(as_text=True)
    assert "has-band" not in html
    assert "seal-whole" not in html


def test_input_limit_matches_the_answer_length(client):
    add_puzzle()
    html = client.get("/").get_data(as_text=True)
    assert 'maxlength="3"' in html
    assert 'data-letters="3"' in html


def test_input_limit_counts_letters_not_words(client):
    add_puzzle(answer="GÖK YÜZÜ", enumeration="3,4", clue="Mavi örtü", definition="Mavi örtü")
    html = client.get("/").get_data(as_text=True)
    assert 'maxlength="7"' in html
    assert 'data-letters="7"' in html
