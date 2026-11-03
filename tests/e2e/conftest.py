"""A real server, a real browser and a database of their own."""

import itertools
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from playwright.sync_api import expect
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

from muamma import clock
from muamma.extensions import db
from muamma.models import Player, Puzzle

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_SCRIPT = Path(__file__).with_name("server.py")
SECRET_KEY = "e2e-only-not-a-real-key"
STARTUP_TIMEOUT = 60.0
ASSERTION_TIMEOUT = 10_000
RESOURCE_ECHO = "Failed to load resource"

_addresses = itertools.count(1)


# Database


def _database_url():
    """The e2e database address, never the development or production one."""
    raw = os.environ.get("E2E_DATABASE_URL")
    if not raw:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
        raw = os.environ.get("E2E_DATABASE_URL")

    if raw:
        url = make_url(raw)
    else:
        base = os.environ.get("DATABASE_URL")
        if not base:
            pytest.fail("set DATABASE_URL or E2E_DATABASE_URL to run the browser tests")
        url = make_url(base)
        url = url.set(database=f"{url.database}_e2e")

    if "e2e" not in (url.database or ""):
        pytest.fail(
            f"refusing to touch the database {url.database!r}: "
            "the name of the e2e database has to contain 'e2e'"
        )
    return url


def _create_database(url):
    """Create the e2e database when it is not there yet."""
    engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            )
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def e2e_app():
    """Flask app on the migrated e2e database, used to seed and clear data."""
    from flask_migrate import upgrade

    from muamma import create_app
    from muamma.config import Config

    url = _database_url()
    _create_database(url)

    class SeedConfig(Config):
        SECRET_KEY = SECRET_KEY
        SQLALCHEMY_DATABASE_URI = url.render_as_string(hide_password=False)
        RATELIMIT_STORAGE_URI = "memory://"

    app = create_app(SeedConfig)
    with app.app_context():
        upgrade(directory=str(PROJECT_ROOT / "migrations"))
    return app


@pytest.fixture(autouse=True)
def clean_database(e2e_app):
    """Every test starts with an empty database."""
    with e2e_app.app_context():
        db.session.execute(
            text("TRUNCATE puzzles, players, plays, events RESTART IDENTITY CASCADE")
        )
        db.session.commit()
    yield


# Server


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_up(health_url, process, log):
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"the e2e server stopped:\n{log.read_text(errors='replace')}")
        try:
            with urllib.request.urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError(f"the e2e server never answered:\n{log.read_text(errors='replace')}")


@pytest.fixture(scope="session")
def live_server(e2e_app, tmp_path_factory):
    """The app in its own process, served the way production serves it."""
    port = _free_port()
    address = f"http://127.0.0.1:{port}"
    log = tmp_path_factory.mktemp("e2e-server") / "server.log"

    environment = {
        **os.environ,
        "E2E_DATABASE_URL": e2e_app.config["SQLALCHEMY_DATABASE_URI"],
        "E2E_SECRET_KEY": SECRET_KEY,
        "E2E_SITE_URL": address,
        "E2E_PORT": str(port),
        "FLASK_DEBUG": "0",
        "PYTHONUNBUFFERED": "1",
        # a script runs with its own directory on the path, not the project root
        "PYTHONPATH": str(PROJECT_ROOT),
    }

    with log.open("wb") as sink:
        process = subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            env=environment,
            stdout=sink,
            stderr=subprocess.STDOUT,
        )
        try:
            _wait_until_up(f"{address}/health", process, log)
            yield address
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


@pytest.fixture(scope="session")
def base_url(live_server):
    """Where page.goto() resolves relative addresses against."""
    return live_server


@pytest.fixture(scope="session", autouse=True)
def _assertion_timeout():
    expect.set_options(timeout=ASSERTION_TIMEOUT)


@pytest.fixture
def client_address():
    """One address per test, so real rate limits cannot leak between them."""
    number = next(_addresses)
    return f"198.51.{number // 254}.{number % 254 + 1}"


@pytest.fixture
def context(new_context, client_address):
    """A fresh cookieless player with a rate limit bucket of its own."""
    return new_context(extra_http_headers={"X-Forwarded-For": client_address})


# What the browser complains about


class PageGuard:
    """Browser-side trouble; a test can allow the failures it asks for."""

    def __init__(self):
        self.page_errors = []
        self.console_errors = []
        self.responses = []
        self.failures = []
        self._allowed = []

    def allow(self, status, url_part):
        """Permit one expected failed response, as 409 on /letter."""
        self._allowed.append((status, url_part))

    def on_page_error(self, error):
        self.page_errors.append(f"page error: {error}")

    def on_console(self, message):
        # a failed request is already recorded, with its address, by on_response
        if message.type == "error" and not message.text.startswith(RESOURCE_ECHO):
            self.console_errors.append(f"console error: {message.text}")

    def on_response(self, response):
        if response.status >= 400:
            self.responses.append((response.status, response.url))

    def on_request_failed(self, request):
        self.failures.append(f"request failed: {request.url} ({request.failure})")

    def _is_allowed(self, status, url):
        return any(status == allowed and part in url for allowed, part in self._allowed)

    def problems(self):
        bad_responses = [
            f"{status} from {url}"
            for status, url in self.responses
            if not self._is_allowed(status, url)
        ]
        return [*self.page_errors, *self.console_errors, *bad_responses, *self.failures]


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    setattr(item, f"_report_{call.when}", report)
    return report


@pytest.fixture(autouse=True)
def guard(page, request):
    """Page errors, console errors and failed requests fail the test."""
    watcher = PageGuard()
    page.on("pageerror", watcher.on_page_error)
    page.on("console", watcher.on_console)
    page.on("response", watcher.on_response)
    page.on("requestfailed", watcher.on_request_failed)

    yield watcher

    report = getattr(request.node, "_report_call", None)
    if report is not None and not report.passed:
        return
    problems = watcher.problems()
    assert not problems, "the browser reported:\n" + "\n".join(problems)


# Puzzles the tests own

DAILY = {
    "clue": "Bozuk kalem, söz demek",
    "definition": "söz",
    "answer": "KELAM",
    "enumeration": "5",
    "hints": ["'Bozuk' harflerin karışacağını söylüyor.", "Cevap K ile başlıyor."],
    "explanation": "KALEM'in harfleri karışınca KELAM olur. Tanım: söz.",
    "technique": "anagram",
}

ARCHIVE = {
    "clue": "Karıncanın içinde saklanan bal yapıcı",
    "definition": "bal yapıcı",
    "answer": "ARI",
    "enumeration": "3",
    "hints": ["'İçinde saklanan' gizli bir kelimeye işaret ediyor."],
    "explanation": "kARInca kelimesinin içinde ARI saklı. Tanım: bal yapıcı.",
    "technique": "hidden",
}

PRACTICE = {
    "clue": "Satıcıda saklı binek",
    "definition": "binek",
    "answer": "AT",
    "enumeration": "2",
    "hints": ["'Saklı' kelimesi gizli bir kelimeye işaret ediyor."],
    "explanation": "sATıcıda kelimesinin içinde AT saklı. Tanım: binek.",
    "technique": "hidden",
}

TWELVE = {
    "clue": "Başkentlerde duran uzun söz",
    "definition": "uzun söz",
    "answer": "BAŞKENTLERDE",
    "enumeration": "12",
    "hints": [],
    "explanation": "On iki harfli bir cevap. Tanım: uzun söz.",
    "technique": "hidden",
}

FIFTEEN = {
    "clue": "Karşılaştırmalı okuma, en uzun söz",
    "definition": "en uzun söz",
    "answer": "KARŞILAŞTIRMALI",
    "enumeration": "15",
    "hints": [],
    "explanation": "On beş harfli bir cevap. Tanım: en uzun söz.",
    "technique": "hidden",
}


@pytest.fixture
def today(e2e_app):
    with e2e_app.app_context():
        return clock.today()


@pytest.fixture
def seed(e2e_app, clean_database):
    """Insert a puzzle and hand back its plain values."""

    def _seed(fields, **overrides):
        values = {
            "kind": "daily",
            "status": "ready",
            "difficulty": 2,
            "publish_date": None,
            **fields,
            **overrides,
        }
        with e2e_app.app_context():
            puzzle = Puzzle(**values)
            db.session.add(puzzle)
            db.session.commit()
            return SimpleNamespace(id=puzzle.id, **values)

    return _seed


@pytest.fixture
def daily(seed, today):
    """Today's puzzle, the one the streak depends on."""
    return seed(DAILY, publish_date=today)


@pytest.fixture
def archive(seed, today):
    return seed(ARCHIVE, publish_date=today - timedelta(days=3))


@pytest.fixture
def practice(seed):
    return seed(PRACTICE, kind="practice")


@pytest.fixture
def player(e2e_app):
    """The streak of the player this browser created."""

    def _set_streak(value, day):
        with e2e_app.app_context():
            row = db.session.scalars(select(Player)).one()
            row.current_streak = value
            row.max_streak = max(row.max_streak, value)
            row.last_streak_date = day
            db.session.commit()

    return SimpleNamespace(set_streak=_set_streak)


# The puzzle card as the player sees it


class Game:
    """Locators for one puzzle card."""

    def __init__(self, page):
        self.page = page
        self.section = page.locator(".puzzle")
        self.input = self.section.locator(".guess-form input")
        self.check = self.section.locator(".guess-form button[type=submit]")
        self.feedback = self.section.locator(".feedback")
        self.clue = self.section.locator(".clue")
        self.definition = self.section.locator(".clue-text mark.definition")
        self.tile_box = self.section.locator(".tiles")
        self.tiles = self.section.locator(".tile")
        self.filled = self.section.locator(".tile.filled")
        self.helpers = self.section.locator(".helpers")
        self.hint_button = self.section.locator("[data-action=hint]")
        self.letter_button = self.section.locator("[data-action=letter]")
        self.reveal_button = self.section.locator("[data-action=reveal]")
        self.hints = self.section.locator(".hints li")
        self.wrong_guesses = self.section.locator(".wrong-guesses li")
        self.solution = self.section.locator(".solution")
        self.answer = self.solution.locator(".answer")
        self.explanation = self.solution.locator(".explanation")
        self.show_result = self.solution.locator(".result-open")
        self.result = self.section.locator("dialog.result")
        self.confirm = self.section.locator("dialog.confirm")
        self.streak = page.locator(".streak-count")

    def idle(self):
        """The card drops anything clicked while it is busy with the last action."""
        expect(self.section).not_to_have_attribute("data-busy", "1")

    def guess(self, text, *, enter=False):
        """Type an answer and send it, by Enter or by the button."""
        self.idle()
        self.input.fill(text)
        if enter:
            self.input.press("Enter")
        else:
            self.check.click()

    def assist_button(self, action):
        return self.section.locator(f"[data-action={action}]")

    def assist(self, action):
        """Click an assist button in the middle of its label.

        Harf aç and Mührü aç wrap their label in a span, so the click lands
        below the button and the handler has to walk back up to it. The
        middle of the label is where a player aims, so it is what the tests
        click.
        """
        self.idle()
        button = self.assist_button(action)
        label = button.locator("span:visible")
        (label if label.count() else button).click()


@pytest.fixture
def game(page):
    return Game(page)
