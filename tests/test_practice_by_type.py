import pytest
from sqlalchemy import select

from muamma.admin.forms import TECHNIQUES
from muamma.extensions import db
from muamma.guide import GROUPS
from muamma.models import Puzzle
from tests.helpers import TODAY, add_puzzle


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def add_practice(technique, **overrides):
    fields = {
        "kind": "practice",
        "publish_date": None,
        "technique": technique,
        "answer": "ARI",
        "enumeration": "3",
        "clue": f"{technique} için bir ipucu: karıncanın içinde saklanan bal yapıcı",
        "definition": "bal yapıcı",
    }
    fields.update(overrides)
    return add_puzzle(**fields)


def landed_on(client, query=""):
    response = client.get(f"/tadimlik{query}")
    assert response.status_code == 302
    puzzle_id = int(response.headers["Location"].rsplit("/", 1)[-1])
    return db.session.get(Puzzle, puzzle_id)


def test_new_types_are_on_the_page(client):
    html = client.get("/nasil-oynanir").get_data(as_text=True)

    for name in ("Eşanlamlılar", "Yabancı kelimeler", "Harf adları"):
        assert name in html
    assert "parçanın kendisi küçük bir tanımdır" in html
    assert "ipucu hangi dil olduğunu söyler" in html
    assert "harflerin okunuşudur" in html
    assert "0 bir O, 1 bir I olabilir" in html


def test_new_examples_show_their_answers(client):
    html = client.get("/nasil-oynanir").get_data(as_text=True)
    for answer in ("ODAK", "LALE", "DEVE"):
        assert f"<strong>{answer}</strong>" in html


def test_button_appears_only_for_types_that_have_one(client):
    add_practice("anagram")
    html = client.get("/nasil-oynanir").get_data(as_text=True)

    assert 'href="/tadimlik?teknik=anagram"' in html
    assert "teknik=container" not in html
    assert html.count("Bu türden bir tadımlık çöz") == 1


def test_no_buttons_without_practice_puzzles(client):
    html = client.get("/nasil-oynanir").get_data(as_text=True)
    assert "Bu türden bir tadımlık çöz" not in html


def test_technique_leads_to_that_kind_of_puzzle(client):
    add_practice("anagram")
    wanted = add_practice("container", answer="ÇAM", clue="Kaçamakta gizlenen ağaç", definition="ağaç")
    add_practice("deletion", answer="KUM", clue="Kumaşın başında bir tane", definition="bir tane")

    assert landed_on(client, "?teknik=container").id == wanted.id


def test_unknown_technique_falls_back(client):
    only = add_practice("anagram")
    assert landed_on(client, "?teknik=boyle-bir-teknik-yok").id == only.id
    assert landed_on(client, "?teknik=").id == only.id


def test_technique_with_nothing_left_falls_back(client):
    anagram = add_practice("anagram")
    container = add_practice("container", answer="ÇAM", clue="Kaçamakta gizlenen ağaç", definition="ağaç")

    client.post(f"/api/puzzles/{container.id}/guess", json={"guess": "çam"})
    assert landed_on(client, "?teknik=container").id == anagram.id


def test_practice_done_when_nothing_is_left(client):
    puzzle = add_practice("anagram")
    client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": "arı"})

    html = client.get("/tadimlik?teknik=anagram").get_data(as_text=True)
    assert "Hepsini çözdün" in html


def test_every_guide_technique_exists_in_the_admin_list(client):
    known = {value for value, _ in TECHNIQUES}
    for group in GROUPS:
        for kind in group["types"]:
            assert kind["technique"] in known, kind["key"]


def test_existing_technique_values_are_untouched(client):
    known = {value for value, _ in TECHNIQUES}
    for value in (
        "anagram",
        "hidden",
        "homophone",
        "charade",
        "container",
        "deletion",
        "reversal",
        "double_definition",
        "cryptic_definition",
        "andlit",
        "other",
    ):
        assert value in known

    assert db.session.scalar(select(Puzzle)) is None
