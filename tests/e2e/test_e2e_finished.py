"""What a reload does to a puzzle that is already finished."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

SETTLE = 400


def test_a_reload_keeps_the_finished_puzzle(page, daily, game):
    page.goto("/")
    game.guess(daily.answer)
    expect(game.result).to_be_visible()
    game.result.locator(".result-close").click()
    expect(game.result).to_be_hidden()

    page.reload()
    expect(game.solution).to_be_visible()
    expect(game.answer).to_have_text(daily.answer)
    expect(game.explanation).to_have_text(daily.explanation)
    expect(game.feedback).to_have_text("Doğru!")
    expect(game.input).to_be_hidden()
    expect(game.helpers).to_be_hidden()
    expect(game.streak).to_have_text("1")
    expect(page.locator("body")).to_have_attribute("data-state", "opened")


def test_the_result_window_does_not_open_itself_after_a_reload(page, daily, game):
    page.goto("/")
    game.guess(daily.answer)
    expect(game.result).to_be_visible()
    game.result.locator(".result-close").click()

    page.reload()
    expect(game.show_result).to_be_visible()
    # nothing should open the window on its own, so give it the chance to
    page.wait_for_timeout(SETTLE)
    expect(game.result).to_be_hidden()

    game.show_result.click()
    expect(game.result).to_be_visible()
    expect(game.result.locator(".result-title")).to_have_text("Tebrikler! Muamma çözüldü")
    expect(game.result.locator(".result-streak")).to_have_text("1")


def test_a_finished_puzzle_cannot_be_guessed_again(page, daily, game):
    page.goto("/")
    game.guess(daily.answer)
    expect(game.answer).to_have_text(daily.answer)

    page.reload()
    expect(game.input).to_be_hidden()
    expect(game.helpers).to_be_hidden()
