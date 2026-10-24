# Muamma

[![Tests](https://github.com/izamaeta/muamma-cryptic/actions/workflows/test.yml/badge.svg)](https://github.com/izamaeta/muamma-cryptic/actions/workflows/test.yml)

Muamma is a daily Turkish cryptic clue game. One clue is published each
day: it reads like an ordinary phrase but hides a second set of
instructions — an anagram, a hidden word, a reversal — that spells the
answer. Players get one puzzle a day, a few assists if they want them, and
a streak for solving on the day.

Live at **https://muamma.app**.

## Features

- A daily puzzle, with the answer and explanation withheld from the page
  and the API until the player finishes.
- Assists that cost something: a hint, a single opening letter, or
  revealing the answer, which ends the streak.
- Streaks and personal statistics, counted only for daily puzzles solved on
  their own date.
- An archive of past days, each with a permanent page.
- Practice puzzles with no date attached, drawn at random or by type.
- A guide to cryptic clue types and a glossary, with twelve worked
  examples.
- A share line that gives away nothing about the answer.
- An admin area for writing, publishing and unpublishing puzzles, with
  warnings for Sundays, long answers and answers already shown in the
  guide.
- Puzzle export and import as JSON, for preparing puzzles off the server.

User-facing text is Turkish throughout; code, identifiers and docs are
English.

## Tech stack

- **Python 3.14**, **Flask 3.1** with server-rendered Jinja templates
- **PostgreSQL 17** via SQLAlchemy 2.1, migrations with Flask-Migrate
  (Alembic)
- **Redis 7** for rate limit counters, through Flask-Limiter
- **gunicorn** behind **Caddy**, orchestrated with **Docker Compose**
- Flask-Login and argon2 for the admin account, Flask-WTF for CSRF
- Hand-written CSS and vanilla JavaScript — no frontend build step, no
  third-party assets or trackers
- **pytest** for the suite

## Architecture

```
Player  →  Cloudflare  →  Caddy  →  gunicorn (muamma)
                            │          │
                            │          ├── PostgreSQL
                            │          └── Redis (rate limits)
                            └── /static/* (direct, cached a year)
```

Cloudflare is the only way in; the origin's security group admits nothing
else. Caddy terminates TLS with a Cloudflare Origin CA certificate, serves
`/static/*` straight from disk, and proxies everything else to gunicorn.
PostgreSQL and Redis publish no ports and are reachable only inside the
compose network. Static URLs carry a content hash (`?v=…`), so they can be
cached for a year and need no purge after a deploy.

The reasoning behind these choices is in [docs/decisions.md](docs/decisions.md).

## Running it locally

PostgreSQL and Redis come from Docker; the app runs on the host.

```bash
cp .env.example .env
docker compose up -d db redis

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

flask db upgrade
flask seed-demo
flask run
```

The site is then at http://127.0.0.1:5000. `.env.example` already points
`DATABASE_URL` and `RATELIMIT_STORAGE_URI` at the ports `compose.yaml`
publishes on localhost (PostgreSQL 15432, Redis 16379), so it works
unedited.

To reach the admin area at `/admin/login`, create an account — the command
asks for the password rather than taking it as an argument:

```bash
flask create-admin you@example.com
```

Other commands:

```bash
flask export-puzzles muamma.puzzles.json          # every puzzle as JSON
flask import-puzzles FILE --start YYYY-MM-DD      # add them back, --dry-run first
flask db migrate -m "..."                         # review the file, then db upgrade
```

An export holds every answer and explanation, so it must never be
committed; `*.puzzles.json` and `exports/` are ignored for that reason.

## Tests and CI

```bash
pytest
```

The suite runs on SQLite and needs no services. GitHub Actions runs it on
every push and pull request, then applies the migrations to a real
PostgreSQL 17 and runs `flask db check` to compare the models against what
the migrations built. A second job builds the Docker image and throws it
away. Nothing in the workflow needs a secret.

## Deployment

[docs/deploy.md](docs/deploy.md) is the runbook: it builds the server from
nothing, sets up Cloudflare and the origin certificate, starts the stack,
and covers updates, backups and restores.

---

© 2026 Ahmet Ata Özdemir. All rights reserved. The source is published for
reference; the puzzles, logo and artwork may not be reused.
