from datetime import date

from flask import url_for

from muamma import clock
from muamma.models import Play, Puzzle


def share_text(puzzle: Puzzle, play: Play, streak: int, url: str) -> str | None:
    """Spoiler-free result summary for a finished daily puzzle."""
    if puzzle.kind != "daily" or play.status == "in_progress":
        return None

    lines = [f"Muamma · {puzzle.publish_date:%d.%m.%Y}"]
    if play.status == "solved":
        lines.append(f"✅ {play.guess_count}. tahminde çözdüm")
        assists = []
        if play.hints_used:
            assists.append(f"💡 {play.hints_used} ipucu")
        if play.letters_revealed:
            assists.append(f"🔤 {play.letters_revealed} harf")
        lines.append(" · ".join(assists) if assists else "🧠 Yardımsız")
    else:
        lines.append("❌ Cevaba baktım")

    if streak:
        lines.append(f"🔥 Seri: {streak}")
    lines.append(url)
    return "\n".join(lines)


def finish_details(puzzle: Puzzle, play: Play, streak: int, today: date) -> dict:
    """Share text and countdown shown after a puzzle is finished."""
    is_today = puzzle.kind == "daily" and puzzle.publish_date == today
    return {
        "share": share_text(puzzle, play, streak, url_for("main.index", _external=True)),
        "next_in": clock.seconds_until_tomorrow() if is_today else None,
    }