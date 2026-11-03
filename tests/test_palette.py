from pathlib import Path

import pytest

from tests.helpers import TODAY, add_puzzle

CSS = Path("muamma/static/css/style.css").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def test_no_turquoise_is_left():
    for gone in ("turquoise", "#1fa5a3", "#3cc7c3", "#178a88", "#bdebea", "#8fd8d6"):
        assert gone not in CSS.lower(), gone


def test_grain_is_off_for_the_admin():
    assert "body.admin::after" in CSS
    assert ".admin .band::after" in CSS
    block = CSS[CSS.index("body.admin::after") :]
    assert block[: block.index("}")].count("content: none") == 1


def test_hidden_elements_really_hide():
    """Author display rules outrank the browser's own [hidden] rule."""
    assert "[hidden] {\n  display: none !important;\n}" in CSS


JS = Path("muamma/static/js/game.js").read_text(encoding="utf-8")


def test_definition_paints_each_line_separately():
    """A wrapped definition used to get one box stretched over both lines."""
    block = CSS[CSS.index(".definition {") : CSS.index(".definition.ink")]
    assert "box-decoration-break: clone" in block
    assert "-webkit-box-decoration-break: clone" in block
    assert "background-image: linear-gradient(var(--def-bg)" in block
    assert ".definition::before" not in CSS


def test_the_ink_fill_animates_the_background():
    block = CSS[CSS.index("@keyframes ink-fill") :]
    block = block[: block.index("\n}\n")]
    assert "background-size: 0% 100%" in block
    assert "transform" not in block


def test_guide_parts_also_clone_across_lines():
    for part in (".part-tanim {", ".part-gosterge {", ".part-malzeme {"):
        block = CSS[CSS.index(part) :]
        block = block[: block.index("\n}\n")]
        assert "box-decoration-break: clone" in block, part


def test_tiles_are_remeasured_when_the_room_changes():
    assert "new ResizeObserver(fitTiles).observe(tileBox)" in JS
    assert "document.fonts.ready.then(fitTiles)" in JS


def test_the_gap_tightens_before_the_row_scrolls():
    assert "--tile-gap" in JS
    assert "var(--tile-gap, 0.25rem)" in CSS


def test_the_row_is_centred_until_it_overflows():
    assert "text-align: center" in CSS[CSS.index(".tiles {") : CSS.index(".tiles.scrollable")]
    scrollable = CSS[CSS.index(".tiles.scrollable {") :]
    assert "text-align: left" in scrollable[: scrollable.index("}")]


THEME_JS = Path("muamma/static/js/theme.js").read_text(encoding="utf-8")
BASE = Path("muamma/templates/base.html").read_text(encoding="utf-8")


def test_dark_is_a_choice_not_a_system_setting():
    assert "prefers-color-scheme" not in CSS
    assert "prefers-color-scheme" not in THEME_JS
    assert ':root[data-theme="dark"] {' in CSS


def test_one_theme_colour_matching_the_light_band():
    assert BASE.count('name="theme-color"') == 1
    assert '<meta name="theme-color" content="#081F5C">' in BASE
