from flask import Blueprint

from muamma.extensions import db, login_manager
from muamma.models import Admin

bp = Blueprint("admin", __name__)


@login_manager.user_loader
def load_admin(admin_id):
    try:
        return db.session.get(Admin, int(admin_id))
    except ValueError:
        return None


from muamma.admin import routes  # noqa: E402, F401