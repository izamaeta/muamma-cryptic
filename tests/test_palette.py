import re
from pathlib import Path

import pytest

from tests.helpers import TODAY, add_puzzle

CSS = Path("muamma/static/css/style.css").read_text(encoding="utf-8")
SEAL = Path("muamma/templates/partials/_seal.html").read_text(encoding="utf-8")
BROKEN = Path("muamma/templates/partials/_seal_broken.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def test_no_turquoise_is_left():
    for gone in ("turquoise", "#1fa5a3", "#3cc7c3", "#178a88", "#bdebea", "#8fd8d6"):
        assert gone not in CSS.lower(), gone


def test_seal_carries_a_gradient_coloured_from_css():
    for markup in (SEAL, BROKEN):
        assert 'gradientUnits="userSpaceOnUse"' in markup
        for stop in ("seal-stop-light", "seal-stop-mid", "seal-stop-deep"):
            assert f'class="{stop}"' in markup
        assert "stop-color" not in markup  # the colours live in the stylesheet

    for stop in ("seal-stop-light", "seal-stop-mid", "seal-stop-deep"):
        assert f".{stop} {{" in CSS


def test_the_two_seals_use_different_gradient_ids():
    ids = re.findall(r'radialGradient id="([^"]+)"', SEAL + BROKEN)
    assert len(ids) == 2
    assert len(set(ids)) == 2


def test_seal_has_its_emboss_and_rim():
    for markup in (SEAL, BROKEN):
        assert 'class="seal-emboss"' in markup
        assert 'class="seal-edge"' in markup
    assert ".seal-emboss {" in CSS
    assert ".seal-edge {" in CSS


def test_both_seals_are_on_a_game_page(client):
    add_puzzle()
    html = client.get("/").get_data(as_text=True)
    assert 'id="muhur-g"' in html
    assert 'id="muhur-kirik-g"' in html


def test_grain_is_off_for_the_admin():
    assert "body.admin::after" in CSS
    assert ".admin .band::after" in CSS
    block = CSS[CSS.index("body.admin::after") :]
    assert block[: block.index("}")].count("content: none") == 1


def test_hidden_elements_really_hide():
    """Author display rules outrank the browser's own [hidden] rule."""
    assert "[hidden] {\n  display: none !important;\n}" in CSS
