from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from muamma.extensions import db
from muamma.models import Event, Play, Player
from muamma.share import play_duration
from muamma.timing import MAX_AGE, SESSION_KEY
from tests.helpers import TODAY, add_puzzle


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


def guess(client, puzzle, value):
    return client.post(f"/api/puzzles/{puzzle.id}/guess", json={"guess": value})


def count(model):
    return db.session.scalar(select(func.count()).select_from(model))


def test_guess_reports_the_duration(client):
    puzzle = add_puzzle()
    data = guess(client, puzzle, "arı").get_json()
    assert isinstance(data["duration"], int)
    assert data["duration"] >= 0


def test_reveal_reports_the_duration_and_counts(client):
    puzzle = add_puzzle()
    client.post(f"/api/puzzles/{puzzle.id}/hint")
    data = client.post(f"/api/puzzles/{puzzle.id}/reveal").get_json()

    assert isinstance(data["duration"], int)
    assert data["hints"] == 1
    assert data["letters"] == 0
    assert data["guesses"] == 0


def test_duration_counts_from_the_page_opening(client):
    puzzle = add_puzzle()
    opened = datetime.now(UTC) - timedelta(minutes=4)
    with client.session_transaction() as session:
        session[SESSION_KEY] = {str(puzzle.id): opened.timestamp()}

    data = guess(client, puzzle, "arı").get_json()
    assert data["duration"] >= 4 * 60


@pytest.mark.parametrize(
    "offset",
    [MAX_AGE + timedelta(minutes=1), -timedelta(hours=2)],
)
def test_stale_and_future_open_times_are_ignored(client, offset):
    puzzle = add_puzzle()
    with client.session_transaction() as session:
        session[SESSION_KEY] = {str(puzzle.id): (datetime.now(UTC) - offset).timestamp()}

    data = guess(client, puzzle, "arı").get_json()
    assert data["duration"] < 60


def test_play_duration_handles_naive_timestamps():
    play = Play(
        started_at=datetime(2026, 10, 10, 12, 0, 0),
        finished_at=datetime(2026, 10, 10, 12, 1, 30, tzinfo=UTC),
    )
    assert play_duration(play) == 90


def test_play_duration_is_none_while_unfinished():
    assert play_duration(Play(started_at=datetime.now(UTC))) is None


def test_page_views_create_no_rows(client):
    puzzle = add_puzzle(publish_date=TODAY - timedelta(days=1))
    practice = add_puzzle(kind="practice", publish_date=None)

    for path in ("/", f"/bulmaca/{puzzle.publish_date.isoformat()}", f"/tadimlik/{practice.id}"):
        assert client.get(path).status_code == 200

    assert count(Player) == 0
    assert count(Play) == 0
    assert count(Event) == 0


def test_finished_puzzle_page_carries_the_result(client):
    puzzle = add_puzzle()
    guess(client, puzzle, "arı")

    html = client.get("/").get_data(as_text=True)
    assert 'data-ready="1"' in html
    assert "Tebrikler! Muamma çözüldü" in html
    assert ">Sonucu göster<" in html
    assert '<dd class="result-guesses">1</dd>' in html


def test_unfinished_puzzle_page_has_no_result(client):
    add_puzzle()
    html = client.get("/").get_data(as_text=True)
    assert 'data-ready="0"' in html
    assert "Tebrikler" not in html


def test_revealed_puzzle_result_does_not_congratulate(client):
    puzzle = add_puzzle()
    client.post(f"/api/puzzles/{puzzle.id}/reveal")

    html = client.get("/").get_data(as_text=True)
    assert "Mühür açıldı" in html
    assert "Tebrikler" not in html


def test_practice_result_offers_another_puzzle(client):
    puzzle = add_puzzle(kind="practice", publish_date=None)
    guess(client, puzzle, "arı")

    html = client.get(f"/tadimlik/{puzzle.id}").get_data(as_text=True)
    assert "Başka bir tadımlık" in html
    assert "Sonucu paylaş" not in html
    assert "Yeni muammaya" not in html


def test_archive_result_replaces_the_streak_row(client):
    puzzle = add_puzzle(publish_date=TODAY - timedelta(days=1))
    guess(client, puzzle, "arı")

    html = client.get(f"/bulmaca/{puzzle.publish_date.isoformat()}").get_data(as_text=True)
    assert "Arşiv çözümleri seriye sayılmaz" in html
    assert "result-streak" not in html


def confirm_note(html):
    panel = html[html.index('class="confirm"') : html.index("</dialog>")]
    start = panel.index('class="result-note"')
    return panel[start : panel.index("</p>", start)]


def test_daily_confirm_warns_about_the_streak(client):
    add_puzzle()
    note = confirm_note(client.get("/").get_data(as_text=True))
    assert "Cevabı görürsen serin sıfırlanır." in note


def test_practice_confirm_warns_about_the_puzzle(client):
    puzzle = add_puzzle(kind="practice", publish_date=None)
    note = confirm_note(client.get(f"/tadimlik/{puzzle.id}").get_data(as_text=True))
    assert "Cevabı görürsen bu bulmacayı çözmüş sayılmazsın." in note


def test_archive_confirm_warns_about_the_puzzle(client):
    puzzle = add_puzzle(publish_date=TODAY - timedelta(days=1))
    html = client.get(f"/bulmaca/{puzzle.publish_date.isoformat()}").get_data(as_text=True)
    assert "Cevabı görürsen bu bulmacayı çözmüş sayılmazsın." in confirm_note(html)


def test_confirm_offers_cancel_and_reveal(client):
    add_puzzle()
    html = client.get("/").get_data(as_text=True)
    panel = html[html.index('class="confirm"') : html.index("</dialog>")]

    assert "Mührü açmak istediğine emin misin?" in panel
    assert '<button value="no" class="confirm-cancel" autofocus>Vazgeç</button>' in panel
    assert '<button value="yes" class="confirm-reveal">Mührü aç</button>' in panel


def test_wrong_guesses_survive_a_reload(client):
    puzzle = add_puzzle()
    guess(client, puzzle, "çam")
    guess(client, puzzle, "kum")

    html = client.get("/").get_data(as_text=True)
    listing = html[html.index('class="wrong-guesses"') : html.index("</ul>")]
    assert listing.index("ÇAM") < listing.index("KUM")


def test_correct_guess_is_not_listed_as_wrong(client):
    puzzle = add_puzzle()
    guess(client, puzzle, "çam")
    guess(client, puzzle, "arı")

    html = client.get("/").get_data(as_text=True)
    listing = html[html.index('class="wrong-guesses"') : html.index("</ul>")]
    assert "ÇAM" in listing
    assert "ARI" not in listing
