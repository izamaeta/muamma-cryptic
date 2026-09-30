from datetime import date

import pytest

from muamma.text import normalize_answer, turkish_long_date


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("arı", "ARI"),
        ("ARI", "ARI"),
        ("istanbul", "İSTANBUL"),
        ("ıspanak", "ISPANAK"),
        ("  kelam ", "KELAM"),
        ("gök yüzü", "GÖKYÜZÜ"),
        ("kâr", "KAR"),
        ("şeker-çiçek", "ŞEKERÇİÇEK"),
    ],
)
def test_normalize_answer(raw, expected):
    assert normalize_answer(raw) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (date(2026, 1, 1), "1 Ocak 2026"),
        (date(2026, 9, 29), "29 Eylül 2026"),
        (date(2026, 12, 31), "31 Aralık 2026"),
    ],
)
def test_turkish_long_date(value, expected):
    assert turkish_long_date(value) == expected