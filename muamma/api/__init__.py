from flask import Blueprint

bp = Blueprint("api", __name__)

from muamma.api import routes  # noqa: E402, F401