"""The furniture around the puzzle: stats, theme and the phone menu."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

PHONE = {"viewport": {"width": 390, "height": 844}}


def test_the_stats_window_starts_empty_and_counts_a_solve(page, daily, game):
    page.goto("/")
    stats = page.locator("dialog.stats-window")
    open_stats = page.locator(".header-tools .stats-open")

    open_stats.click()
    expect(stats).to_be_visible()
    expect(stats.locator(".stats-empty")).to_be_visible()
    stats.locator(".result-close").click()
    expect(stats).to_be_hidden()

    game.guess(daily.answer)
    expect(game.result).to_be_visible()
    page.reload()

    open_stats.click()
    expect(stats).to_be_visible()
    expect(stats.locator(".stats-empty")).to_be_hidden()
    expect(stats.locator("[data-key=daily_played]")).to_have_text("1")
    expect(stats.locator("[data-key=daily_solved]")).to_have_text("1")
    expect(stats.locator("[data-key=solve_rate]")).to_have_text("100")
    expect(stats.locator("[data-key=current_streak]")).to_have_text("1")


def test_the_dark_theme_survives_a_reload(page, daily):
    page.goto("/")
    root = page.locator("html")
    toggle = page.locator(".header-tools .theme-toggle")

    expect(toggle).to_have_attribute("aria-pressed", "false")
    expect(root).not_to_have_attribute("data-theme", "dark")

    toggle.click()
    expect(root).to_have_attribute("data-theme", "dark")
    expect(toggle).to_have_attribute("aria-pressed", "true")

    page.reload()
    expect(root).to_have_attribute("data-theme", "dark")
    expect(toggle).to_have_attribute("aria-pressed", "true")

    toggle.click()
    expect(root).to_have_attribute("data-theme", "light")
    page.reload()
    expect(root).to_have_attribute("data-theme", "light")


@pytest.mark.browser_context_args(**PHONE)
def test_the_phone_menu_opens_the_navigation(page, daily):
    page.goto("/")
    menu = page.locator(".nav-menu")
    panel = menu.locator(".nav-menu-panel")

    expect(page.locator(".site-nav")).to_be_hidden()
    expect(panel).to_be_hidden()

    menu.locator("summary").click()
    expect(panel).to_be_visible()
    expect(panel.get_by_role("link", name="Arşiv")).to_be_visible()
    expect(panel.get_by_role("link", name="Tadımlık")).to_be_visible()
    expect(panel.get_by_role("button", name="İstatistik")).to_be_visible()


@pytest.mark.browser_context_args(**PHONE)
def test_the_phone_menu_opens_the_stats_window(page, daily):
    page.goto("/")
    page.locator(".nav-menu summary").click()
    page.locator(".nav-menu-panel .stats-open").click()
    expect(page.locator("dialog.stats-window")).to_be_visible()
