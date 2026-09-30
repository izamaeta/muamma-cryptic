import unicodedata
from datetime import date

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


_TURKISH_MONTHS = (
    "Ocak",
    "Şubat",
    "Mart",
    "Nisan",
    "Mayıs",
    "Haziran",
    "Temmuz",
    "Ağustos",
    "Eylül",
    "Ekim",
    "Kasım",
    "Aralık",
)


def turkish_long_date(value: date) -> str:
    """Day, Turkish month name and year, as in 29 Eylül 2026."""
    return f"{value.day} {_TURKISH_MONTHS[value.month - 1]} {value.year}"


def minutes_seconds(total: int | None) -> str:
    """Whole seconds as m:ss, or h:mm:ss once past an hour."""
    if total is None:
        return ""
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"