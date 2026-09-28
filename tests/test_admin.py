import pytest
from sqlalchemy import select

from muamma.cli import create_admin
from muamma.extensions import db
from muamma.models import Admin
from muamma.security import hash_password

EMAIL = "admin@example.com"
PASSWORD = "correct horse battery"


@pytest.fixture
def admin(app):
    admin = Admin(email=EMAIL, password_hash=hash_password(PASSWORD))
    db.session.add(admin)
    db.session.commit()
    return admin


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/admin/login", data={"email": email, "password": password})


def test_dashboard_requires_login(client):
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_login_and_logout(client, admin):
    assert login(client).status_code == 302
    assert client.get("/admin/").status_code == 200

    client.post("/admin/logout")
    assert client.get("/admin/").status_code == 302


@pytest.mark.parametrize(
    ("email", "password"),
    [(EMAIL, "wrong password"), ("nobody@example.com", PASSWORD)],
)
def test_failed_login_gives_same_message(client, admin, email, password):
    html = login(client, email, password).get_data(as_text=True)
    assert "E-posta veya şifre hatalı." in html
    assert client.get("/admin/").status_code == 302


def test_email_is_case_insensitive(client, admin):
    login(client, email="Admin@Example.com")
    assert client.get("/admin/").status_code == 200


def test_admin_session_expires(client, admin):
    login(client)
    with client.session_transaction() as sess:
        sess["admin_since"] = 0
    assert client.get("/admin/").status_code == 302


def test_admin_pages_are_not_indexed(client):
    response = client.get("/admin/login")
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"


def test_create_admin_command(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        create_admin, ["New@Example.com"], input="long enough pass\nlong enough pass\n"
    )
    assert result.exit_code == 0
    assert db.session.scalar(select(Admin.email)) == "new@example.com"


def test_create_admin_rejects_short_password(app):
    runner = app.test_cli_runner()
    result = runner.invoke(create_admin, ["a@example.com"], input="short\nshort\n")
    assert result.exit_code != 0