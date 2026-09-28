from flask import Flask

from muamma.config import Config
from muamma.extensions import csrf, db, login_manager, migrate


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    for key in ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI"):
        if not app.config.get(key):
            raise RuntimeError(f"{key} is not set")

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    from muamma import models  # noqa: F401
    from muamma.admin import bp as admin_bp
    from muamma.api import bp as api_bp
    from muamma.cli import create_admin, seed_demo
    from muamma.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.cli.add_command(seed_demo)
    app.cli.add_command(create_admin)

    return app