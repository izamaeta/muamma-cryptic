"""The İpucu and Harf aç buttons."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

PHONE_HEIGHT = 844
WIDTHS = [320, 360, 390, 430]
LABEL_BREAKPOINT = 400

# the labels shorten under the breakpoint, so the span a player's finger
# lands on is not the same one at every width
LABELS = {
    "letter": {"wide": "Harf aç", "narrow": "Harf"},
    "reveal": {"wide": "Mührü aç", "narrow": "Mühür"},
}


def assert_the_action_started(game, action):
    """Proof that the click reached the handler, whichever assist it was."""
    if action == "letter":
        expect(game.filled).to_have_count(1)
    else:
        expect(game.confirm).to_be_visible()


def test_the_first_hint_names_the_definition_and_highlights_it(page, daily, game):
    page.goto("/")
    expect(game.definition).to_have_count(0)

    game.assist("hint")
    expect(game.hints).to_have_text([f"Tanım: {daily.definition}"])
    expect(game.definition).to_have_text(daily.definition)
    expect(game.clue).to_contain_text(daily.clue)

    game.assist("hint")
    expect(game.hints).to_have_text(
        [f"Tanım: {daily.definition}", daily.hints[0]]
    )


def test_the_hint_and_its_highlight_survive_a_reload(page, daily, game):
    page.goto("/")
    game.assist("hint")
    expect(game.definition).to_have_text(daily.definition)

    page.reload()
    expect(game.hints).to_have_text([f"Tanım: {daily.definition}"])
    expect(game.definition).to_have_text(daily.definition)


@pytest.mark.parametrize("action", ["letter", "reveal"])
def test_clicking_the_label_of_an_assist_button_works(page, daily, game, action):
    page.goto("/")
    game.assist(action)
    assert_the_action_started(game, action)


@pytest.mark.parametrize("action", ["letter", "reveal"])
@pytest.mark.parametrize("width", WIDTHS)
def test_the_assist_labels_work_at_every_phone_width(
    page, daily, game, width, action
):
    page.set_viewport_size({"width": width, "height": PHONE_HEIGHT})
    page.goto("/")

    label = game.assist_button(action).locator("span:visible")
    expect(label).to_have_count(1)
    expect(label).to_have_text(
        LABELS[action]["narrow" if width <= LABEL_BREAKPOINT else "wide"]
    )

    game.assist(action)
    assert_the_action_started(game, action)


def test_the_letter_button_never_opens_the_last_letter(page, daily, game, guard):
    page.goto("/")
    length = len(daily.answer)

    for opened in range(1, length):
        game.assist("letter")
        expect(game.filled).to_have_count(opened)

    last = game.tiles.nth(length - 1)
    expect(last.locator(".letter")).to_have_text("")

    guard.allow(409, "/letter")
    game.assist("letter")
    expect(game.feedback).to_have_text("Daha fazla harf açılamaz.")
    expect(game.filled).to_have_count(length - 1)
    expect(last.locator(".letter")).to_have_text("")


def test_opened_letters_are_still_there_after_a_reload(page, daily, game):
    page.goto("/")
    game.assist("letter")
    expect(game.filled).to_have_count(1)
    opened = game.section.locator(".tile.filled .letter").inner_text()

    page.reload()
    expect(game.filled).to_have_count(1)
    expect(game.section.locator(".tile.filled .letter")).to_have_text(opened)
    expect(game.answer).to_be_hidden()
