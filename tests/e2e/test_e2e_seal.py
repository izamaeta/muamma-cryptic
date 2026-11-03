"""Mührü aç: the confirmation window and what it costs."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_giving_up_on_the_confirmation_keeps_the_answer_hidden(page, daily, game):
    page.goto("/")
    game.assist("reveal")

    expect(game.confirm).to_be_visible()
    expect(game.confirm.locator(".result-title")).to_have_text(
        "Mührü açmak istediğine emin misin?"
    )
    expect(game.confirm.locator(".result-note")).to_have_text(
        "Cevabı görürsen serin sıfırlanır."
    )

    game.confirm.locator(".confirm-cancel").click()
    expect(game.confirm).to_be_hidden()
    expect(game.solution).to_be_hidden()
    expect(game.input).to_be_visible()
    expect(game.helpers).to_be_visible()
    expect(page.locator("body")).to_have_attribute("data-state", "sealed")


def test_opening_the_seal_shows_the_answer_and_resets_the_streak(
    page, daily, game, player, today
):
    page.goto("/")
    game.guess("KALEM", enter=True)
    expect(game.feedback).to_have_text("Olmadı, tekrar dene.")

    player.set_streak(3, today)
    page.reload()
    expect(game.streak).to_have_text("3")

    game.assist("reveal")
    expect(game.confirm).to_be_visible()
    game.confirm.locator(".confirm-reveal").click()

    expect(game.feedback).to_have_text("Cevap:")
    expect(game.answer).to_have_text(daily.answer)
    expect(game.explanation).to_have_text(daily.explanation)
    expect(game.input).to_be_hidden()
    expect(game.helpers).to_be_hidden()

    expect(game.result).to_be_visible()
    expect(game.result.locator(".result-title")).to_have_text("Mühür açıldı")
    expect(game.result.locator(".result-streak")).to_have_text("0")
    expect(game.streak).to_have_text("0")


def test_the_reset_streak_is_still_zero_after_a_reload(page, daily, game, player, today):
    page.goto("/")
    game.guess("KALEM", enter=True)
    expect(game.feedback).to_have_text("Olmadı, tekrar dene.")

    player.set_streak(3, today)
    page.reload()
    game.assist("reveal")
    game.confirm.locator(".confirm-reveal").click()
    expect(game.answer).to_have_text(daily.answer)

    page.reload()
    expect(game.streak).to_have_text("0")
    expect(game.answer).to_have_text(daily.answer)
