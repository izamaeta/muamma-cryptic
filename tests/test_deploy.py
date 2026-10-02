import importlib
import re
from pathlib import Path

import pytest

from muamma import create_app
from muamma.config import TestConfig

ROOT = Path(__file__).resolve().parent.parent

PRODUCTION_ENV = {
    "SECRET_KEY": "not-the-real-one",
    "DATABASE_URL": "postgresql+psycopg://muamma:pw@db:5432/muamma",
    "RATELIMIT_STORAGE_URI": "redis://redis:6379/0",
    "SITE_URL": "https://muamma.example/",
    "SESSION_COOKIE_SECURE": "1",
    "HSTS_ENABLED": "1",
    "TRUSTED_PROXY_HOPS": "2",
    "APP_TIMEZONE": "Europe/Istanbul",
}


@pytest.fixture
def production_config(monkeypatch):
    """Config as it is read in production: from the environment, at import."""
    for name, value in PRODUCTION_ENV.items():
        monkeypatch.setenv(name, value)

    import muamma.config

    try:
        yield importlib.reload(muamma.config).Config
    finally:
        # Leave the module as the rest of the suite expects to find it.
        monkeypatch.undo()
        importlib.reload(muamma.config)


def test_production_settings_load(production_config):
    assert production_config.SECRET_KEY == "not-the-real-one"
    assert production_config.SESSION_COOKIE_SECURE is True
    assert production_config.HSTS_ENABLED is True
    assert production_config.TRUSTED_PROXY_HOPS == 2
    assert production_config.SESSION_COOKIE_SAMESITE == "Lax"
    # Addresses are built by joining, so a trailing slash would double up.
    assert production_config.SITE_URL == "https://muamma.example"
    assert production_config.RATELIMIT_STORAGE_URI == "redis://redis:6379/0"


def test_development_defaults_are_not_secure():
    """The flags are off unless the environment turns them on."""
    import muamma.config

    plain = importlib.reload(muamma.config).Config
    assert plain.SESSION_COOKIE_SECURE is False
    assert plain.HSTS_ENABLED is False
    assert plain.TRUSTED_PROXY_HOPS == 0


class ProxiedConfig(TestConfig):
    # Player -> Cloudflare -> Caddy -> gunicorn
    TRUSTED_PROXY_HOPS = 2


def address_client(config):
    app = create_app(config)

    @app.get("/nerden")
    def nerden():
        from flask import request

        return request.remote_addr or ""

    return app.test_client()


def test_client_address_comes_from_the_proxy_chain():
    client = address_client(ProxiedConfig)
    response = client.get(
        "/nerden",
        headers={"X-Forwarded-For": "203.0.113.7, 172.68.1.1"},
        environ_base={"REMOTE_ADDR": "172.18.0.9"},
    )
    assert response.text == "203.0.113.7"


def test_a_forged_header_cannot_claim_an_address():
    """Counting from the right is what makes the chain trustworthy.

    Cloudflare appends the real client address to whatever the client sent,
    and Caddy appends Cloudflare's. Two hops back from the end is therefore
    always the address Cloudflare saw, never the one the client typed.
    """
    client = address_client(ProxiedConfig)
    response = client.get(
        "/nerden",
        headers={"X-Forwarded-For": "9.9.9.9, 203.0.113.7, 172.68.1.1"},
        environ_base={"REMOTE_ADDR": "172.18.0.9"},
    )
    assert response.text == "203.0.113.7"


def test_without_trusted_hops_the_header_is_ignored():
    client = address_client(TestConfig)
    response = client.get(
        "/nerden",
        headers={"X-Forwarded-For": "9.9.9.9"},
        environ_base={"REMOTE_ADDR": "172.18.0.9"},
    )
    assert response.text == "172.18.0.9"


def test_static_addresses_carry_a_content_hash(app):
    with app.test_request_context():
        from flask import url_for

        address = url_for("static", filename="css/style.css")

    assert re.fullmatch(r"/static/css/style\.css\?v=[0-9a-f]{8}", address), address


def test_the_hash_follows_the_file(app, tmp_path, monkeypatch):
    from flask import url_for

    from muamma import assets

    monkeypatch.setattr(assets, "_versions", {})
    monkeypatch.setattr(app, "static_folder", str(tmp_path))
    written = tmp_path / "deneme.css"

    with app.test_request_context():
        written.write_text("a{}", encoding="utf-8")
        first = url_for("static", filename="deneme.css")
        assets._versions.clear()
        written.write_text("a{color:red}", encoding="utf-8")
        second = url_for("static", filename="deneme.css")

    assert first != second


def test_a_missing_file_gets_a_plain_address(app):
    with app.test_request_context():
        from flask import url_for

        assert url_for("static", filename="yok/boyle/bir/dosya.css") == (
            "/static/yok/boyle/bir/dosya.css"
        )


def test_production_compose_opens_only_the_web_ports():
    compose = (ROOT / "compose.prod.yaml").read_text(encoding="utf-8")
    # Only published ports have a colon; bare numbers are 'expose', which
    # stays inside the network.
    published = set(re.findall(r'^\s+- "(\d+:\d+(?:/udp)?)"', compose, re.MULTILINE))
    assert published == {"80:80", "443:443", "443:443/udp"}
    # The database and the cache are reachable from inside the network only.
    assert "5432:" not in compose
    assert "6379:" not in compose


def test_production_compose_keeps_services_alive_and_rotates_logs():
    compose = (ROOT / "compose.prod.yaml").read_text(encoding="utf-8")
    assert compose.count("restart: unless-stopped") == 5
    assert 'max-size: "10m"' in compose
    assert "healthcheck:" in compose


def test_the_production_example_has_the_keys_and_none_of_the_values():
    lines = (ROOT / ".env.production.example").read_text(encoding="utf-8").splitlines()
    settings = dict(
        line.split("=", 1) for line in lines if line and not line.startswith("#")
    )

    assert settings["SESSION_COOKIE_SECURE"] == "1"
    assert settings["HSTS_ENABLED"] == "1"
    assert settings["TRUSTED_PROXY_HOPS"] == "2"
    assert settings["FLASK_DEBUG"] == "0"
    assert settings["SITE_URL"].startswith("https://")
    assert settings["BACKUP_KEEP_DAYS"] == "30"

    # The example carries no secret, and no AWS key belongs here at all:
    # the server reads its own IAM role.
    assert settings["SECRET_KEY"] == ""
    assert settings["POSTGRES_PASSWORD"] == ""
    assert not [name for name in settings if "AWS_ACCESS" in name or "AWS_SECRET" in name]
