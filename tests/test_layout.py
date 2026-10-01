import pytest

from muamma.admin.services import long_word_warning
from muamma.models import Puzzle
from muamma.puzzles import tile_groups
from tests.helpers import TODAY, add_puzzle


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def test_reading_pages_use_the_wide_layout(client):
    add_puzzle()
    for path in ("/nasil-oynanir", "/muamma-nedir", "/gizlilik", "/arsiv"):
        html = client.get(path).get_data(as_text=True)
        assert '<body class="reading"' in html, path


def test_game_pages_keep_their_own_layout(client):
    puzzle = add_puzzle()
    practice = add_puzzle(kind="practice", publish_date=None)

    for path in ("/", f"/tadimlik/{practice.id}"):
        html = client.get(path).get_data(as_text=True)
        assert '<body class="has-band"' in html, path
        assert "reading" not in html.split("<body", 1)[1][:60], path
    assert puzzle.id


def test_long_answers_keep_their_word_groups():
    puzzle = Puzzle(answer="A" * 15, enumeration="15")
    groups = tile_groups(puzzle, set())
    assert len(groups) == 1
    assert len(groups[0]) == 15

    three = Puzzle(answer="A" * 15, enumeration="5,5,5")
    groups = tile_groups(three, set())
    assert [len(group) for group in groups] == [5, 5, 5]


def test_long_answer_renders_one_group_per_word(client):
    add_puzzle(
        answer="GÖKYÜZÜNÜN MAVİSİ",
        enumeration="10,6",
        clue="Uzun bir cevap denemesi",
        definition="Uzun bir cevap",
    )
    html = client.get("/").get_data(as_text=True)

    assert html.count('class="tile-group"') == 2
    assert html.count('class="tile"') == 16


def test_helpers_hold_every_button_in_one_row(client):
    practice = add_puzzle(kind="practice", publish_date=None)
    html = client.get(f"/tadimlik/{practice.id}").get_data(as_text=True)
    helpers = html[html.index('class="helpers"') : html.index("</div>", html.index('class="helpers"'))]

    assert helpers.count("<button") == 4
    assert 'class="glossary-open"' in helpers
    assert '<span class="narrow">Harf</span>' in helpers
    assert '<span class="narrow">Mühür</span>' in helpers


def test_daily_helpers_have_no_glossary(client):
    add_puzzle()
    html = client.get("/").get_data(as_text=True)
    helpers = html[html.index('class="helpers"') : html.index("</div>", html.index('class="helpers"'))]

    assert helpers.count("<button") == 3
    assert "glossary-open" not in helpers


@pytest.mark.parametrize(
    ("enumeration", "warned"),
    [("3", False), ("12", False), ("13", True), ("5,5,5", False), ("4,13", True)],
)
def test_long_word_warning(enumeration, warned):
    puzzle = Puzzle(enumeration=enumeration)
    assert (long_word_warning(puzzle) is not None) is warned


def test_saving_a_long_word_warns_but_succeeds(client):
    from muamma.extensions import db
    from muamma.models import Admin
    from muamma.security import hash_password

    password = "correct horse battery"
    db.session.add(Admin(email="a@example.com", password_hash=hash_password(password)))
    db.session.commit()
    client.post("/admin/login", data={"email": "a@example.com", "password": password})

    response = client.post(
        "/admin/puzzles/new",
        data={
            "kind": "practice",
            "status": "ready",
            "clue": "Çok uzun bir kelimenin saklandığı ipucu",
            "definition": "Çok uzun",
            "answer": "A" * 14,
            "enumeration": "14",
            "hints": "",
            "explanation": "örnek",
            "technique": "anagram",
            "difficulty": "2",
            "publish_date": "",
        },
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)

    assert "Bulmaca kaydedildi." in html
    assert "14 harflik bir kelime var" in html
