from muamma import create_app
from muamma.config import TestConfig
from muamma.extensions import db
from tests.helpers import add_puzzle


class CsrfConfig(TestConfig):
    WTF_CSRF_ENABLED = True


class LimitedConfig(TestConfig):
    RATELIMIT_ENABLED = True


def make_app(config):
    app = create_app(config)
    app.app_context().push()
    db.create_all()
    return app


def test_api_requires_csrf_token():
    app = make_app(CsrfConfig)
    puzzle = add_puzzle()
    response = app.test_client().post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": "arı"})
    assert response.status_code == 400


def test_security_headers(client):
    headers = client.get("/").headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" not in headers


def test_admin_login_is_rate_limited():
    client = make_app(LimitedConfig).test_client()
    data = {"email": "nobody@example.com", "password": "wrong"}
    statuses = [client.post("/admin/login", data=data).status_code for _ in range(6)]
    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429


def test_api_is_rate_limited():
    client = make_app(LimitedConfig).test_client()
    puzzle = add_puzzle(kind="practice", publish_date=None)
    responses = [
        client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": "x"})
        for _ in range(31)
    ]
    assert responses[29].status_code == 400
    assert responses[30].status_code == 429
    assert responses[30].get_json() == {"error": "rate_limited"}


def test_oversized_request_is_rejected(client):
    response = client.post("/admin/login", data={"email": "x" * 70_000})
    assert response.status_code == 413