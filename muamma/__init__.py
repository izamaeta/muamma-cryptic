from flask import Flask

from muamma.config import Config


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set")

    from muamma.main import bp as main_bp

    app.register_blueprint(main_bp)

    return app