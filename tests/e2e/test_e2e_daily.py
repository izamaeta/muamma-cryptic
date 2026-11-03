"""The daily puzzle: sending a guess with Enter and with the button."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_the_daily_puzzle_arrives_sealed(page, daily, game):
    page.goto("/")
    expect(game.clue).to_contain_text(daily.clue)
    expect(game.input).to_be_visible()
    expect(game.helpers).to_be_visible()
    expect(game.solution).to_be_hidden()
    expect(game.definition).to_have_count(0)
    expect(game.filled).to_have_count(0)
    expect(game.streak).to_have_text("0")
    expect(page.locator("body")).to_have_attribute("data-state", "sealed")


def test_a_wrong_guess_sent_with_enter_clears_the_input(page, daily, game):
    page.goto("/")
    game.guess("KALEM", enter=True)

    expect(game.feedback).to_have_text("Olmadı, tekrar dene.")
    expect(game.input).to_have_value("")
    expect(game.filled).to_have_count(0)
    expect(game.wrong_guesses).to_have_text(["KALEM"])
    expect(game.solution).to_be_hidden()
    expect(game.input).to_be_visible()
    expect(page.locator("body")).to_have_attribute("data-state", "sealed")


@pytest.mark.parametrize("enter", [False, True], ids=["button", "enter"])
def test_the_right_answer_solves_the_puzzle(page, daily, game, enter):
    page.goto("/")
    game.guess(daily.answer, enter=enter)

    expect(game.feedback).to_have_text("Doğru!")
    expect(game.solution).to_be_visible()
    expect(game.answer).to_have_text(daily.answer)
    expect(game.explanation).to_have_text(daily.explanation)
    expect(game.input).to_be_hidden()
    expect(game.helpers).to_be_hidden()
    expect(page.locator("body")).to_have_attribute("data-state", "opened")

    expect(game.result).to_be_visible()
    expect(game.result.locator(".result-title")).to_have_text("Tebrikler! Muamma çözüldü")
    expect(game.result.locator(".result-guesses")).to_have_text("1")
    expect(game.result.locator(".result-streak")).to_have_text("1")
    expect(game.streak).to_have_text("1")


def test_wrong_guesses_are_still_there_after_a_reload(page, daily, game):
    page.goto("/")
    game.guess("KALEM", enter=True)
    expect(game.wrong_guesses).to_have_text(["KALEM"])
    game.guess("MEKAL", enter=True)
    expect(game.wrong_guesses).to_have_text(["KALEM", "MEKAL"])

    page.reload()
    expect(game.wrong_guesses).to_have_text(["KALEM", "MEKAL"])
    expect(game.input).to_be_visible()
    expect(game.solution).to_be_hidden()
