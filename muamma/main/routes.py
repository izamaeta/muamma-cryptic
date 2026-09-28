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
from muamma.gameplay import get_play, random_practice_id
from muamma.main import bp
from muamma.models import Puzzle
from muamma.players import current_player
from muamma.puzzles import daily_puzzle_for, is_playable, puzzle_view
from muamma.stats import player_stats


@bp.app_context_processor
def inject_globals():
    player = current_player()
    site_url = current_app.config["SITE_URL"]
    return {
        "streak": player.displayed_streak(clock.today()) if player else 0,
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
        context.update(puzzle_view(puzzle, get_play(player, puzzle), today))
    return render_template("index.html", **context)


@bp.get("/tadimlik")
def practice_random():
    puzzle_id = random_practice_id(current_player())
    if puzzle_id is None:
        return render_template("practice_done.html")
    return redirect(url_for("main.practice", puzzle_id=puzzle_id))


@bp.get("/tadimlik/<int:puzzle_id>")
def practice(puzzle_id):
    today = clock.today()
    puzzle = db.session.get(Puzzle, puzzle_id)
    if puzzle is None or puzzle.kind != "practice" or not is_playable(puzzle, today):
        abort(404)
    play = get_play(current_player(), puzzle)
    return render_template("practice.html", **puzzle_view(puzzle, play, today))


@bp.get("/istatistik")
def stats():
    player = current_player()
    data = player_stats(player, clock.today()) if player else None
    return render_template("stats.html", stats=data)


@bp.get("/nasil-oynanir")
def how_to_play():
    return render_template("how_to_play.html")



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
        url_for("main.privacy"),
    ]
    body = render_template("sitemap.xml", urls=[site + path for path in paths])
    return Response(body, mimetype="application/xml")


@bp.get("/health")
def health():
    return {"status": "ok"}