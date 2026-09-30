import pytest

from muamma.models import Puzzle
from muamma.puzzles import clue_parts, letter_pattern, tile_groups
from tests.helpers import TODAY, add_puzzle


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def make(**fields):
    base = {"clue": "Karıncanın içinde saklanan bal yapıcı", "definition": "bal yapıcı"}
    base.update(fields)
    return Puzzle(answer="GÖK YÜZÜ", enumeration="3,4", **base)


def test_tile_groups_follow_enumeration():
    assert tile_groups(make(), {0, 1}) == [["G", "Ö", ""], ["", "", "", ""]]
    assert letter_pattern(make(), {0, 1, 2, 3}) == "GÖK Y___"


def test_tile_groups_take_positions_in_any_order():
    assert tile_groups(make(), {2, 4}) == [["", "", "K"], ["", "Ü", "", ""]]
    assert letter_pattern(make(), {6}) == "___ ___Ü"


def test_clue_parts_uses_turkish_case_rules():
    puzzle = make(clue="İçinde saklı BAL YAPICI", definition="bal yapıcı")
    assert clue_parts(puzzle) == ("İçinde saklı ", "BAL YAPICI", "")


def test_clue_parts_without_definition():
    assert clue_parts(make(definition=None)) is None


def test_definition_is_highlighted_only_after_hint(client):
    puzzle = add_puzzle()
    assert "<mark" not in client.get("/").get_data(as_text=True)

    data = client.post(f"/api/puzzles/{puzzle.id}/hint").get_json()
    assert data["highlight"] == ["Karıncanın içinde saklanan ", "bal yapıcı", ""]
    html = client.get("/").get_data(as_text=True)
    assert '<mark class="definition">bal yapıcı</mark>' in html


def test_tiles_hide_letters_until_finished(client):
    puzzle = add_puzzle()
    html = client.get("/").get_data(as_text=True)
    assert html.count('class="tile"') == 3
    assert 'data-given="A"' not in html

    client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": "arı"})
    html = client.get("/").get_data(as_text=True)
    assert 'data-given="A"' in html