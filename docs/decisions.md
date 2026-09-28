# Design decisions

## Docker Compose for local and production

The app and PostgreSQL run in containers so the local setup matches the
server. The web container runs gunicorn as a non-root user. PostgreSQL is
pinned to 17, stores data in a named volume, and its port is bound to
localhost only.

The host port for PostgreSQL is 15432 to avoid clashing with a local
PostgreSQL install on the default port.


## Data model

Four tables: `puzzles`, `players`, `plays` (one row per player and puzzle,
holding current state) and `events` (append-only log for analytics).
Keeping them separate lets gameplay queries stay small while analytics
keeps the full history, including wrong guesses.

A player row is created on the first real action (guess or hint), not on
page view. Crawlers do not keep cookies and would otherwise create a new
player on every visit.

Streak values are written when a daily puzzle is solved and validated on
read: if the last streak day is before yesterday, the displayed streak is
zero.

Rules such as "ready daily puzzles need a date" and "one daily puzzle per
date" are enforced with database constraints, not only in application
code. Puzzles that have plays cannot be deleted.

## Answer normalization

Answers are compared after Turkish-aware uppercasing (i/İ, ı/I),
flattening circumflex vowels and removing everything except letters.
Python's `str.upper()` is not locale-aware and maps `i` to `I`.