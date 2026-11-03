"""Tadımlık puzzles and the archive, neither of which touches the streak."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_a_practice_puzzle_can_be_solved(page, practice, game):
    page.goto("/tadimlik")
    assert f"/tadimlik/{practice.id}" in page.url
    expect(game.section).to_have_attribute("data-puzzle-id", str(practice.id))

    game.guess(practice.answer)
    expect(game.feedback).to_have_text("Doğru!")
    expect(game.answer).to_have_text(practice.answer)
    expect(game.explanation).to_have_text(practice.explanation)

    expect(game.result).to_be_visible()
    expect(game.result.locator(".result-action")).to_have_text("Başka bir tadımlık")
    expect(game.streak).to_have_text("0")


def test_a_practice_puzzle_has_no_share_button_or_countdown(page, practice, game):
    page.goto("/tadimlik")
    game.guess(practice.answer)
    expect(game.result).to_be_visible()
    expect(game.section.locator(".share-button")).to_have_count(0)
    expect(game.section.locator(".countdown")).to_have_count(0)


def test_solving_an_archive_puzzle_leaves_the_streak_alone(
    page, archive, game, player, today
):
    page.goto(f"/bulmaca/{archive.publish_date.isoformat()}")
    game.guess("ARA", enter=True)
    expect(game.feedback).to_have_text("Olmadı, tekrar dene.")

    player.set_streak(2, today)
    page.reload()
    expect(game.streak).to_have_text("2")

    game.guess(archive.answer)
    expect(game.feedback).to_have_text("Doğru!")
    expect(game.answer).to_have_text(archive.answer)

    expect(game.result).to_be_visible()
    expect(game.result.locator(".result-note")).to_have_text(
        "Arşiv çözümleri seriye sayılmaz"
    )
    expect(game.result.locator(".result-streak")).to_have_count(0)
    expect(game.streak).to_have_text("2")

    page.reload()
    expect(game.streak).to_have_text("2")
    expect(game.answer).to_have_text(archive.answer)
