import re
from datetime import date

from flask import (
    Response,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

from muamma import clock
from muamma.extensions import db
from muamma.gameplay import get_play, play_status_by_puzzle, random_practice_id
from muamma.main import bp
from muamma.models import Puzzle
from muamma.players import current_player
from muamma.puzzles import (
    archive_neighbours,
    archive_puzzles,
    daily_puzzle_for,
    is_playable,
    practice_techniques,
    puzzle_view,
)
from muamma.timing import mark_opened

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@bp.app_context_processor
def inject_globals():
    player = current_player()
    site_url = current_app.config["SITE_URL"]
    return {
        "streak": player.displayed_streak(clock.today()) if player else 0,
        "today": clock.today(),
        "site_url": site_url,
        "canonical_url": site_url + request.path,
    }

@bp.app_errorhandler(429)
def too_many_requests(error):
    return render_template("429.html"), 429



@bp.app_errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@bp.get("/")
def index():
    today = clock.today()
    player = current_player()
    puzzle = daily_puzzle_for(today)

    context = {"puzzle": None, "new_visitor": player is None}
    if puzzle is not None:
        mark_opened(puzzle.id)
        context.update(puzzle_view(puzzle, get_play(player, puzzle), today))
    return render_template("index.html", **context)


@bp.get("/tadimlik")
def practice_random():
    player = current_player()
    wanted = request.args.get("teknik")

    puzzle_id = random_practice_id(player, wanted)
    if puzzle_id is None and wanted:
        puzzle_id = random_practice_id(player)
    if puzzle_id is None:
        return render_template("practice_done.html")
    return redirect(url_for("main.practice", puzzle_id=puzzle_id))


@bp.get("/tadimlik/<int:puzzle_id>")
def practice(puzzle_id):
    today = clock.today()
    puzzle = db.session.get(Puzzle, puzzle_id)
    if puzzle is None or puzzle.kind != "practice" or not is_playable(puzzle, today):
        abort(404)
    mark_opened(puzzle.id)
    play = get_play(current_player(), puzzle)
    return render_template("practice.html", **puzzle_view(puzzle, play, today))


def archive_date(raw: str) -> date:
    """Only plain YYYY-MM-DD; other spellings ISO parsing allows are 404."""
    if not ISO_DATE.fullmatch(raw):
        abort(404)
    try:
        return date.fromisoformat(raw)
    except ValueError:
        abort(404)


@bp.get("/arsiv")
def archive():
    today = clock.today()
    return render_template(
        "archive.html",
        puzzles=archive_puzzles(today),
        statuses=play_status_by_puzzle(current_player()),
    )


@bp.get("/bulmaca/<day>")
def archive_puzzle(day):
    today = clock.today()
    published_on = archive_date(day)

    if published_on == today:
        return redirect(url_for("main.index"))
    if published_on > today:
        abort(404)

    puzzle = daily_puzzle_for(published_on)
    if puzzle is None:
        abort(404)

    mark_opened(puzzle.id)
    previous, following = archive_neighbours(published_on, today)
    play = get_play(current_player(), puzzle)
    return render_template(
        "archive_puzzle.html",
        previous=previous,
        following=following,
        **puzzle_view(puzzle, play, today),
    )


@bp.get("/muamma-nedir")
def about():
    return render_template("about.html")


@bp.get("/istatistik")
def stats():
    """The page became a dialog; keep the old address pointing somewhere."""
    return redirect(url_for("main.index"), code=301)


@bp.get("/nasil-oynanir")
def how_to_play():
    return render_template("how_to_play.html", practice_techniques=practice_techniques())



@bp.get("/gizlilik")
def privacy():
    return render_template("privacy.html", contact_email=current_app.config["CONTACT_EMAIL"])


@bp.get("/robots.txt")
def robots():
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/",
        f"Sitemap: {current_app.config['SITE_URL']}/sitemap.xml",
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@bp.get("/sitemap.xml")
def sitemap():
    site = current_app.config["SITE_URL"]
    paths = [
        url_for("main.index"),
        url_for("main.how_to_play"),
        url_for("main.archive"),
        url_for("main.about"),
        url_for("main.privacy"),
    ]
    urls = [{"loc": site + path} for path in paths]
    urls += [
        {
            "loc": site + url_for("main.archive_puzzle", day=puzzle.publish_date.isoformat()),
            "lastmod": max(puzzle.publish_date, puzzle.updated_at.date()),
        }
        for puzzle in archive_puzzles(clock.today())
    ]
    body = render_template("sitemap.xml", urls=urls)
    return Response(body, mimetype="application/xml")


@bp.get("/health")
def health():
    return {"status": "ok"}