from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from muamma.config import Config
from muamma.extensions import csrf, db, limiter, login_manager, migrate
from muamma.headers import apply_security_headers
from muamma.text import minutes_seconds, turkish_long_date


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    for key in ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI"):
        if not app.config.get(key):
            raise RuntimeError(f"{key} is not set")

    hops = app.config["TRUSTED_PROXY_HOPS"]
    if hops:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    app.after_request(apply_security_headers)
    app.add_template_filter(turkish_long_date, "long_date")
    app.add_template_filter(minutes_seconds, "mmss")

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