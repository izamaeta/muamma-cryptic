import unicodedata

_TURKISH_UPPER = str.maketrans(
    {
        "i": "İ",
        "ı": "I",
        "â": "A",
        "Â": "A",
        "î": "İ",
        "Î": "İ",
        "û": "U",
        "Û": "U",
    }
)


def turkish_upper(value: str) -> str:
    return value.translate(_TURKISH_UPPER).upper()


def normalize_answer(value: str) -> str:
    """Uppercase with Turkish casing rules and keep letters only."""
    value = unicodedata.normalize("NFC", value)
    return "".join(ch for ch in turkish_upper(value) if ch.isalpha())