import pytest

from muamma.text import normalize_answer


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