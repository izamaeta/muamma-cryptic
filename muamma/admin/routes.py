import time

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select

from muamma import clock
from muamma.admin import bp
from muamma.admin.forms import LoginForm, PuzzleForm
from muamma.admin.services import (
    STOCK_WARNING_DAYS,
    is_locked,
    lock_fields,
    save_puzzle,
    stock_days,
    upcoming,
)
from muamma.extensions import db, limiter
from muamma.models import Admin, Puzzle, utcnow
from muamma.security import check_login

SESSION_KEY = "admin_since"


@bp.before_request
def expire_admin_session():
    if not current_user.is_authenticated:
        return
    max_age = current_app.config["ADMIN_SESSION_HOURS"] * 3600
    if time.time() - session.get(SESSION_KEY, 0) > max_age:
        logout_user()
        session.pop(SESSION_KEY, None)


@bp.after_request
def no_index(response):
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute;20 per hour", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        admin = db.session.scalar(select(Admin).where(Admin.email == email))
        if check_login(admin.password_hash if admin else None, form.password.data):
            login_user(admin)
            session[SESSION_KEY] = time.time()
            admin.last_login_at = utcnow()
            db.session.commit()
            return redirect(url_for("admin.dashboard"))
        flash("E-posta veya şifre hatalı.")

    return render_template("admin/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.pop(SESSION_KEY, None)
    return redirect(url_for("admin.login"))


@bp.get("/")
@login_required
def dashboard():
    today = clock.today()
    stock = stock_days(today)
    return render_template(
        "admin/dashboard.html",
        stock=stock,
        warning=stock < STOCK_WARNING_DAYS,
        calendar=upcoming(today),
    )


@bp.get("/puzzles")
@login_required
def puzzles():
    today = clock.today()
    view = request.args.get("view", "upcoming")
    query = select(Puzzle)

    if view == "past":
        query = query.where(Puzzle.kind == "daily", Puzzle.publish_date < today)
        query = query.order_by(Puzzle.publish_date.desc())
    elif view == "practice":
        query = query.where(Puzzle.kind == "practice").order_by(Puzzle.id.desc())
    elif view == "drafts":
        query = query.where(Puzzle.status == "draft").order_by(Puzzle.id.desc())
    else:
        view = "upcoming"
        query = query.where(Puzzle.kind == "daily", Puzzle.publish_date >= today)
        query = query.order_by(Puzzle.publish_date)

    return render_template(
        "admin/puzzles.html", puzzles=db.session.scalars(query).all(), view=view
    )


@bp.route("/puzzles/new", methods=["GET", "POST"])
@login_required
def puzzle_new():
    form = PuzzleForm()
    if request.method == "GET":
        form.kind.data = request.args.get("kind", "daily")

    if form.validate_on_submit() and save_puzzle(form, None, clock.today()):
        flash("Bulmaca kaydedildi.")
        return redirect(url_for("admin.puzzles"))

    return render_template("admin/puzzle_form.html", form=form, puzzle=None, locked=False)


@bp.route("/puzzles/<int:puzzle_id>", methods=["GET", "POST"])
@login_required
def puzzle_edit(puzzle_id):
    puzzle = db.get_or_404(Puzzle, puzzle_id)
    today = clock.today()
    locked = is_locked(puzzle, today)

    form = PuzzleForm(obj=puzzle)
    if request.method == "GET":
        form.hints.data = "\n".join(puzzle.hints or [])
    if locked:
        lock_fields(form, puzzle)

    if form.validate_on_submit() and save_puzzle(form, puzzle, today):
        flash("Bulmaca güncellendi.")
        return redirect(url_for("admin.puzzles"))

    return render_template(
        "admin/puzzle_form.html", form=form, puzzle=puzzle, locked=locked
    )


@bp.post("/puzzles/<int:puzzle_id>/delete")
@login_required
def puzzle_delete(puzzle_id):
    puzzle = db.get_or_404(Puzzle, puzzle_id)
    if is_locked(puzzle, clock.today()):
        flash("Yayınlanmış ya da oynanmış bir bulmaca silinemez.")
        return redirect(url_for("admin.puzzle_edit", puzzle_id=puzzle.id))

    db.session.delete(puzzle)
    db.session.commit()
    flash("Bulmaca silindi.")
    return redirect(url_for("admin.puzzles"))