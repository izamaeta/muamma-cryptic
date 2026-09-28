import time

from flask import current_app, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select

from muamma.admin import bp
from muamma.admin.forms import LoginForm
from muamma.extensions import db
from muamma.models import Admin, utcnow
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
    return render_template("admin/dashboard.html")