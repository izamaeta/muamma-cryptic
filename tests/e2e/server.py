"""The app served by waitress for the browser tests, on the e2e database."""

import os

from waitress import serve

from muamma import create_app
from muamma.config import Config


class E2EConfig(Config):
    """Real settings on a throwaway database; CSRF and rate limits stay on."""

    SECRET_KEY = os.environ["E2E_SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = os.environ["E2E_DATABASE_URL"]
    SITE_URL = os.environ["E2E_SITE_URL"]
    RATELIMIT_STORAGE_URI = "memory://"
    SESSION_COOKIE_SECURE = False
    HSTS_ENABLED = False
    # the tests speak through X-Forwarded-For, as production does behind Cloudflare
    TRUSTED_PROXY_HOPS = 1


if __name__ == "__main__":
    serve(
        create_app(E2EConfig),
        host="127.0.0.1",
        port=int(os.environ["E2E_PORT"]),
        threads=8,
    )
