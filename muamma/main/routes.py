from flask import render_template

from muamma.main import bp


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/health")
def health():
    return {"status": "ok"}