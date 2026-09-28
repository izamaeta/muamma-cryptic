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


## Daily puzzle and guess checking

"Today" always comes from `clock.today()` in the app timezone, so tests
can pin the date. The page never contains the answer or explanation;
they are returned by the guess endpoint only after a correct guess.

Puzzles that are drafts or scheduled for a later date return 404 from the
API, the same as a missing puzzle, so their existence is not revealed.

Client code lives in static files rather than inline scripts, to allow a
strict Content-Security-Policy later. Server text is inserted with
`textContent`, never as HTML.




## Player identity

The anonymous player id is stored in Flask's signed session cookie, so it
cannot be altered on the client. The cookie is HttpOnly, SameSite=Lax,
Secure in production and lasts 400 days.

## Recording play

Guesses with the wrong letter count are rejected without being recorded,
since they are mostly typos. Each counted guess is logged as an event with
the normalized guess. A finished play rejects further guesses with 409.
Solution text is rendered into the page only for players who finished
the puzzle.

Two simultaneous first requests from the same player could both try to
create a play row; the unique constraint rejects the second one. This is
rare enough to leave for now.



## Assists

The first hint is the definition when the clue has one. Some clues have
no separable definition (cryptic definitions, &lit clues, visual clues
such as HIJKLMNO for WATER), so the definition is optional and those
puzzles start with their own hints.

Letters are revealed left to right and the last one is never revealed,
since that would equal showing the answer. Revealing the answer finishes
the play; for the daily puzzle on its own day it also resets the streak,
so the client asks for confirmation first.

Hints used and letters revealed are stored on the play, so progress is
restored on reload. All API errors are returned as JSON with an `error`
code.

## Practice and stats

`/tadimlik` redirects to a random ready practice puzzle the player has not
finished, so each puzzle has a stable URL. Player stats are computed from
`plays` on request; the numbers are small per player and do not need to be
stored.


## Admin authentication

Admin accounts can only be created with the `create-admin` command on the
server; there is no sign-up page. Passwords are hashed with argon2 and
must be at least 12 characters.

Failed logins return the same message for unknown emails and wrong
passwords, and unknown emails are checked against a dummy hash so both
cases take similar time. After login the user is always sent to the
dashboard; the `next` parameter is ignored to avoid open redirects.

The session cookie is long-lived for players, so admin logins carry their
own timestamp and expire after 12 hours. Admin pages send
`X-Robots-Tag: noindex`. Login rate limiting comes with the security step.

## CSRF

CSRF protection is enabled for every POST, including the game API. Pages
expose the token in a meta tag and the client sends it as `X-CSRFToken`.