import pytest

from muamma.guide import GROUPS, all_indicators, glossary_groups
from tests.helpers import TODAY, add_puzzle


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


@pytest.fixture
def guide_html(client):
    return client.get("/nasil-oynanir").get_data(as_text=True)


def test_the_three_sections_are_on_the_page(guide_html):
    for group in GROUPS:
        assert group["label"] in guide_html
    assert guide_html.count('class="guide-panel"') == 3


def test_every_type_is_on_the_page(guide_html):
    for group in GROUPS:
        for kind in group["types"]:
            assert kind["name"] in guide_html
            assert kind["summary"][:40] in guide_html


def test_every_example_shows_its_answer(guide_html):
    answers = [
        kind["example"]["answer"]
        for group in GROUPS
        for kind in group["types"]
        if kind["example"]
    ]
    assert len(answers) == 9
    for answer in answers:
        assert f"<strong>{answer}</strong>" in guide_html


def test_every_indicator_is_on_the_page(guide_html):
    for word in all_indicators():
        assert f">{word}</span>" in guide_html


def test_anatomy_box_holds_the_three_parts(guide_html):
    box = guide_html[guide_html.index('class="anatomy"') : guide_html.index("</dl>")]

    for part in ("Bozuk", "kalem", "söz"):
        assert f'>{part}</button>' in box
    for role in ("gösterge", "malzeme", "tanım"):
        assert f'<span class="role">{role}</span>' in guide_html


def test_sections_stand_alone_without_scripts(guide_html):
    """The tablist is built by JS, so the markup must read as sections."""
    assert "role=\"tablist\"" not in guide_html
    assert guide_html.count('class="guide-panel-title"') == 3


def test_parts_carry_a_label_next_to_their_colour(guide_html):
    assert 'class="role role-tanim"' in guide_html
    assert 'class="role role-gosterge"' in guide_html
    assert 'class="role role-malzeme"' in guide_html


def test_glossary_is_on_practice_and_archive(client):
    practice = add_puzzle(kind="practice", publish_date=None)
    archive = add_puzzle(
        publish_date=TODAY.replace(day=TODAY.day - 1),
        answer="ÇAM",
        clue="Kaçamakta gizlenen ağaç",
        definition="ağaç",
    )

    for path in (
        f"/tadimlik/{practice.id}",
        f"/bulmaca/{archive.publish_date.isoformat()}",
    ):
        html = client.get(path).get_data(as_text=True)
        assert 'class="glossary"' in html, path
        assert 'class="glossary-open"' in html, path


def test_glossary_stays_out_of_the_daily_puzzle(client):
    add_puzzle()
    html = client.get("/").get_data(as_text=True)

    assert 'class="glossary-open"' not in html
    assert 'class="glossary"' not in html


def test_glossary_lists_every_indicator(client):
    puzzle = add_puzzle(kind="practice", publish_date=None)
    html = client.get(f"/tadimlik/{puzzle.id}").get_data(as_text=True)
    window = html[html.index('class="glossary"') : html.index("</dialog>")]

    for word in all_indicators():
        assert f'data-word="{word}"' in window
    for group in glossary_groups():
        assert group["label"] in window
        for kind in group["types"]:
            assert kind["name"] in window


def test_glossary_is_absent_from_plain_pages(client):
    html = client.get("/gizlilik").get_data(as_text=True)
    assert 'class="glossary-open"' not in html
