from flask import Flask

from muamma.config import Config
from muamma.extensions import db, migrate


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    for key in ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI"):
        if not app.config.get(key):
            raise RuntimeError(f"{key} is not set")

    db.init_app(app)
    migrate.init_app(app, db)
    
    from muamma import models  # noqa: F401

    from muamma.main import bp as main_bp

    app.register_blueprint(main_bp)

    return app