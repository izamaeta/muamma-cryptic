"""The game on a 390x844 phone screen."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

PHONE = {"viewport": {"width": 390, "height": 844}}
SLACK = 1

TWELVE = {
    "clue": "Başkentlerde duran uzun söz",
    "definition": "uzun söz",
    "answer": "BAŞKENTLERDE",
    "enumeration": "12",
    "hints": [],
    "explanation": "On iki harfli bir cevap. Tanım: uzun söz.",
    "technique": "hidden",
}

FIFTEEN = {
    "clue": "Karşılaştırmalı okuma, en uzun söz",
    "definition": "en uzun söz",
    "answer": "KARŞILAŞTIRMALI",
    "enumeration": "15",
    "hints": [],
    "explanation": "On beş harfli bir cevap. Tanım: en uzun söz.",
    "technique": "hidden",
}


def sideways_overflow(page):
    """Pixels the page could be scrolled sideways."""
    return page.evaluate(
        "() => { const root = document.scrollingElement;"
        " return root.scrollWidth - root.clientWidth; }"
    )


def settled(page, game):
    """Wait for the tiles to be measured and fitted."""
    expect(game.input).to_be_visible()
    page.wait_for_function(
        "() => document.querySelector('.tiles').style.getPropertyValue('--tile-size') !== ''"
    )
    assert page.evaluate("() => window.scrollY") == 0


def assert_within_the_screen(page, locator, name):
    box = locator.bounding_box()
    size = page.viewport_size
    assert box is not None, f"{name} has no box"
    assert box["x"] >= -SLACK, f"{name} starts off the left edge at {box['x']}"
    assert box["x"] + box["width"] <= size["width"] + SLACK, (
        f"{name} runs past the right edge to {box['x'] + box['width']}"
    )
    assert box["y"] >= -SLACK, f"{name} starts above the screen at {box['y']}"
    assert box["y"] + box["height"] <= size["height"] + SLACK, (
        f"{name} needs scrolling, it ends at {box['y'] + box['height']}"
    )


@pytest.mark.browser_context_args(**PHONE)
def test_the_phone_screen_does_not_scroll_sideways(page, daily, game):
    page.goto("/")
    settled(page, game)
    assert sideways_overflow(page) <= SLACK


@pytest.mark.browser_context_args(**PHONE)
def test_the_whole_game_fits_on_a_phone_screen(page, daily, game):
    page.goto("/")
    settled(page, game)

    assert_within_the_screen(page, game.clue, "the clue")
    assert_within_the_screen(page, game.tile_box, "the tiles")
    assert_within_the_screen(page, game.input, "the answer box")
    assert_within_the_screen(page, game.helpers, "the assist buttons")

    for action in ("hint", "letter", "reveal"):
        assert_within_the_screen(page, game.assist_button(action), f"the {action} button")


@pytest.mark.browser_context_args(**PHONE)
@pytest.mark.parametrize("fields", [TWELVE, FIFTEEN], ids=["12", "15"])
def test_a_long_answer_does_not_scroll_the_phone_sideways(
    page, seed, today, game, fields
):
    puzzle = seed(fields, publish_date=today)
    page.goto("/")
    settled(page, game)

    expect(game.tiles).to_have_count(len(puzzle.answer))
    assert sideways_overflow(page) <= SLACK
    assert_within_the_screen(page, game.tile_box, "the tiles")
    assert_within_the_screen(page, game.input, "the answer box")
    assert_within_the_screen(page, game.helpers, "the assist buttons")


@pytest.mark.browser_context_args(**PHONE)
def test_a_long_answer_can_be_solved_on_a_phone(page, seed, today, game):
    puzzle = seed(FIFTEEN, publish_date=today)
    page.goto("/")
    settled(page, game)

    game.guess(puzzle.answer)
    expect(game.feedback).to_have_text("Doğru!")
    expect(game.answer).to_have_text(puzzle.answer)
    assert sideways_overflow(page) <= SLACK
