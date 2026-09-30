from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from muamma import create_app
from muamma.config import TestConfig
from muamma.extensions import db
from muamma.admin.services import publish_problem
from muamma.models import Admin, Play, Player
from muamma.security import hash_password
from tests.helpers import TODAY, add_puzzle

PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def log_in(client):
    db.session.add(Admin(email="admin@example.com", password_hash=hash_password(PASSWORD)))
    db.session.commit()
    client.post("/admin/login", data={"email": "admin@example.com", "password": PASSWORD})
    return client


@pytest.fixture
def admin_client(client):
    return log_in(client)


def publish(client, puzzle, back="puzzles"):
    return client.post(
        f"/admin/puzzles/{puzzle.id}/publish", data={"back": back}, follow_redirects=True
    )


def unpublish(client, puzzle, back="puzzles"):
    return client.post(
        f"/admin/puzzles/{puzzle.id}/unpublish", data={"back": back}, follow_redirects=True
    )


def test_practice_draft_goes_live(admin_client):
    puzzle = add_puzzle(kind="practice", status="draft", publish_date=None)
    html = publish(admin_client, puzzle).get_data(as_text=True)

    assert "Bulmaca yayına alındı." in html
    assert puzzle.status == "ready"


def test_dated_daily_draft_goes_live(admin_client):
    puzzle = add_puzzle(status="draft", publish_date=TODAY + timedelta(days=3))
    publish(admin_client, puzzle)
    assert puzzle.status == "ready"


def test_daily_draft_without_a_date_is_refused(admin_client):
    puzzle = add_puzzle(status="draft", publish_date=None)
    html = publish(admin_client, puzzle).get_data(as_text=True)

    assert "Hazır günlük bulmacanın tarihi olmalı." in html
    assert puzzle.status == "draft"


def test_past_date_is_refused(admin_client):
    puzzle = add_puzzle(status="draft", publish_date=TODAY - timedelta(days=1))
    html = publish(admin_client, puzzle).get_data(as_text=True)

    assert "Geçmiş bir tarihe bulmaca konamaz." in html
    assert puzzle.status == "draft"


def test_two_puzzles_cannot_share_a_date(admin_client):
    """Publishing onto a taken date cannot happen: the column is unique."""
    add_puzzle(publish_date=TODAY + timedelta(days=2))
    clash = add_puzzle(
        status="draft",
        publish_date=None,
        answer="ÇAM",
        clue="Kaçamakta gizlenen ağaç",
        definition="ağaç",
    )

    clash.publish_date = TODAY + timedelta(days=2)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

    assert publish_problem(clash, TODAY) == "Hazır günlük bulmacanın tarihi olmalı."


def test_ready_puzzle_can_be_pulled_back(admin_client):
    puzzle = add_puzzle(publish_date=TODAY + timedelta(days=3))
    html = unpublish(admin_client, puzzle).get_data(as_text=True)

    assert "Bulmaca taslağa çekildi." in html
    assert puzzle.status == "draft"


def test_published_puzzle_cannot_be_pulled_back(admin_client):
    puzzle = add_puzzle(publish_date=TODAY)
    html = unpublish(admin_client, puzzle).get_data(as_text=True)

    assert "taslağa çekilemez" in html
    assert puzzle.status == "ready"


def test_played_puzzle_cannot_be_pulled_back(admin_client):
    puzzle = add_puzzle(publish_date=TODAY + timedelta(days=4))
    player = Player()
    db.session.add(player)
    db.session.flush()
    db.session.add(Play(player_id=player.id, puzzle_id=puzzle.id, status="in_progress"))
    db.session.commit()

    html = unpublish(admin_client, puzzle).get_data(as_text=True)
    assert "taslağa çekilemez" in html
    assert puzzle.status == "ready"


def test_publishing_an_easy_sunday_still_warns(admin_client):
    sunday = TODAY + timedelta(days=(6 - TODAY.weekday()) % 7 or 7)
    puzzle = add_puzzle(status="draft", publish_date=sunday, difficulty=1)

    html = publish(admin_client, puzzle).get_data(as_text=True)
    assert "Bulmaca yayına alındı." in html
    assert "haftanın çetin muamması olmalı" in html
    assert puzzle.status == "ready"


def test_buttons_appear_in_all_three_places(admin_client):
    draft = add_puzzle(status="draft", publish_date=TODAY + timedelta(days=5))

    for path in ("/admin/", "/admin/puzzles", f"/admin/puzzles/{draft.id}"):
        html = admin_client.get(path).get_data(as_text=True)
        assert f"/admin/puzzles/{draft.id}/publish" in html, path
        assert 'name="csrf_token"' in html, path


def test_publishing_needs_a_csrf_token():
    class CsrfConfig(TestConfig):
        WTF_CSRF_ENABLED = True

    app = create_app(CsrfConfig)
    app.app_context().push()
    db.create_all()

    client = log_in(app.test_client())
    puzzle = add_puzzle(status="draft", publish_date=TODAY + timedelta(days=3))

    assert client.post(f"/admin/puzzles/{puzzle.id}/publish").status_code == 400
    assert puzzle.status == "draft"
