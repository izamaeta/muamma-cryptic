# Design decisions

## Flask with server-side rendering

Pages are rendered on the server with Jinja templates instead of a
JavaScript single-page app, so search engines can read puzzle and archive
content directly. Flask fits this well and has mature extensions for
sessions, forms and CSRF protection, which the admin panel will need.

## Configuration through environment variables

All settings and secrets come from environment variables. `.env` is used
locally and never committed; `.env.example` lists the required keys.

The local `DATABASE_URL` uses `127.0.0.1` instead of `localhost` and sets
`connect_timeout`. On Windows `localhost` may resolve to IPv6 first and
hang against Docker's port forwarding; the timeout turns any hang into a
clear error.

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
`X-Robots-Tag: noindex`.

## CSRF

CSRF protection is enabled for every POST, including the game API. Pages
expose the token in a meta tag and the client sends it as `X-CSRFToken`.

## Puzzle management

The admin form checks more than required fields: the answer length must
match the enumeration, a definition must appear in the clue, clues without
a definition need at least one hint, and dates cannot be in the past or
already taken. Answers are stored uppercased with Turkish rules.

Published or played puzzles are locked: kind, status, answer, enumeration
and date keep their stored values regardless of what the form submits,
while clue text and explanation stay editable for typo fixes. Locked
puzzles cannot be deleted.

The stock indicator counts consecutive ready days from today rather than
the total number of scheduled puzzles, because a single gap means a day
without a puzzle.

## Rate limiting

Limits are stored in Redis so all gunicorn workers share counters. If
Redis is unavailable, requests are allowed rather than failing; a short
window without limits is better than an outage.

Each game API endpoint allows 30 requests per minute and 500 per hour,
keyed by player id when present and by IP otherwise. Mobile carriers put
many users behind one IP, so IP-only limits would punish unrelated
players. Dropping the cookie does not help an attacker: every new identity
starts with a request counted against the IP. Admin login attempts are
limited to 5 per minute and 20 per hour per IP.

## Security headers and proxies

Every response carries a strict Content-Security-Policy (own scripts and
styles only), nosniff, frame denial and a referrer policy. HSTS is only
enabled in production behind HTTPS. Request bodies are capped at 64 KB.

`X-Forwarded-*` headers are trusted only when `TRUSTED_PROXY_HOPS` is set,
because without a real proxy in front a client could spoof its IP and
bypass rate limits.

## Visual design

A newspaper-puzzle look: paper background, ink text, a deep red accent,
a serif face for clues and a system sans-serif for the interface. Fonts
come from the system rather than a font service, which keeps the CSP
strict, avoids an extra request and sends no visitor data to a third
party. Colors are CSS variables so dark mode only swaps the palette.

Answer tiles mirror what the player types; revealed letters stay dimmed
in place. Tiles are hidden from screen readers and a visually hidden
text pattern carries the same information. Letters appear in the page
source only after they are revealed or the puzzle is finished, and the
definition highlight only after the first hint or on finish.

## Sharing and countdown

Finished daily puzzles offer a spoiler-free summary: date, number of
guesses, assists used and streak, never the answer. The text is built on
the server so it is testable and identical after a reload. Phones use the
native share sheet; other browsers copy to the clipboard.

The countdown to the next puzzle uses seconds computed on the server in
the app timezone, since the visitor's clock or timezone may differ.

## How to play

A dedicated page explains definitions, wordplay types and their indicator
words with Turkish examples. First-time visitors (no player yet) see a
link to it on the home page.