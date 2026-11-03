# Browser tests

The suite under `tests/e2e/` plays the game in a real Chromium against a
real server, so a broken game flow turns CI red even when every unit test
still passes. They are marked `e2e` and the default `pytest` run skips
them; `pytest -m e2e` runs them and nothing else.

## Running them locally

PostgreSQL has to be up, as for any other local work:

```bash
docker compose up -d db
```

The browser is installed once per machine:

```bash
pip install -r requirements-dev.txt
playwright install chromium
```

Then:

```bash
pytest -m e2e                       # the browser tests
pytest                              # everything else, as before
pytest -m e2e --headed              # watch it play
pytest -m e2e -k seal               # one group
```

Useful while writing one:

```bash
pytest -m e2e --tracing on --output e2e-artifacts
playwright show-trace e2e-artifacts/<test>/trace.zip
```

## The database

The tests never touch the development database. They use a database of
their own, `muamma_e2e`, created on first run and migrated with Alembic;
every test starts by truncating it. The name comes from
`E2E_DATABASE_URL`, or from `DATABASE_URL` with `_e2e` appended to the
database name, and a name without `e2e` in it is refused rather than
written to. `.env` is read when neither variable is already set, so no
extra setup is needed locally.

Each test inserts the puzzles it needs, with answers it knows. Nothing
depends on `flask seed-demo`.

## What the tests assume

The server is a separate waitress process, configured like production:
CSRF on, rate limits on, security headers on. Each test gets a new
browser context, so every test is a first-time visitor with no cookies,
and sends its own `X-Forwarded-For` address so the real rate limits
cannot leak from one test into the next.

Every test also fails on a page error, a console error or any failed
request, static files included. A test that expects a failed response
says so:

```python
guard.allow(409, "/letter")
```

## In CI

The `Browser tests` job in `.github/workflows/test.yml` brings up
PostgreSQL 17, creates the database, runs the migrations, installs
Chromium from a cache keyed on `requirements-dev.txt`, and runs
`pytest -m e2e`. When it fails it uploads the traces and screenshots as
the `e2e-artifacts` artifact.

## Known failure

`test_clicking_the_label_of_an_assist_button_works` is an expected
failure. `game.js` reads `event.target` in the assists handler, so a
click that lands on the label inside the **Harf aç** or **Mührü aç**
button never reaches the handler; only the padding around the label
works. The marker is strict, so fixing the handler makes the test pass
and CI will ask for the marker to be removed.
