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


## Technical SEO

Absolute URLs (canonical, sitemap, share cards) are built from the
`SITE_URL` setting instead of the request host, because behind Cloudflare
and a reverse proxy the host seen by the app is not reliable. Each page
defines its title and description once; the Open Graph tags reuse them.

Personal or empty pages (stats, practice done, errors) are marked
`noindex`. `robots.txt` keeps crawlers out of `/admin/` and `/api/`.

## Interface foundation

The visual language itself lives in docs/design.md; these are the
implementation choices behind it.

Page state is a `data-state` attribute on `<body>`, filled by a template
block from the player's play record, so a solved or revealed puzzle still
shows the opened palette after a reload. The theme is a separate
`data-theme` attribute on `<html>`, which keeps the two independent.

Both seals are rendered into the page and `data-state` decides which one
is visible. Swapping the whole seal would mean building SVG in the client,
and the crack is only a graphic, so it reveals nothing about the answer.
The seals are inlined with `{% include %}` rather than `<img>` because
their colours come from CSS variables.

The provenance metadata the seal SVGs shipped with was removed: inlined
into HTML it is no longer file metadata, and it added about 20 KB to every
page render.

`static/js/theme.js` is loaded in `<head>` without `defer` so the stored
theme is applied before the first paint; the toggle is wired on
`DOMContentLoaded`, since the button does not exist yet when the script
runs. Every `localStorage` access is guarded, because private windows can
throw.

The light palette is the default and the system preference is not read at
all. Following `prefers-color-scheme` meant that a reader whose phone is
set to dark never saw the paper the game was designed on, without ever
having asked for the dark one. Dark is still there, one button away, and
the choice is remembered. `theme-color` is therefore a single tag matching
the light band rather than a pair keyed to the system.

Favicons are PNG at 32 and 48 pixels instead of the old SVG, because the
logo is a raster image.

The phone header carries no text navigation, so "Tadımlık" was added to
the footer to keep it reachable.

## Archive and permanent puzzle pages

`/arsiv` lists ready daily puzzles published before today, newest first.
The player's labels come from one query that loads every play as a puzzle
id to status map, so the list does not query per row. There is no paging
yet; puzzles arrive one a day, so a single page stays reasonable for the
first years.

Each past puzzle has a permanent page at `/bulmaca/YYYY-MM-DD`. Only that
plain spelling is accepted: `date.fromisoformat` also parses `20261009`
and week dates, which would give the same puzzle several URLs. Today's
date redirects to the home page for the same reason. Future dates and
drafts are 404, matching the API.

Solving from the archive does not touch the streak, because `finish_play`
only counts a solve when the puzzle's publish date is today. No extra rule
was needed.

The sitemap lists every archive puzzle with
`lastmod = max(publish_date, updated_at)`, so a typo fix on an old puzzle
is visible to crawlers. `updated_at` is stored in UTC and its date is used
as it is; a few hours of drift does not matter for a lastmod.

## Solve time

The time shown after a puzzle is the distance between opening the page and
finishing it. The open time is written to the session cookie when a puzzle
page is rendered, never to the database, so a page view still creates no
rows; crawlers keep no cookies and simply fall back to the play record's
own start. Only the last three puzzles are kept in the cookie, and a value
older than a day or set in the future is ignored.

The play row is created on the first action, so without the cookie the
clock starts there: solving with the first guess then reads as a few
seconds rather than the time spent thinking.

`started_at` and `finished_at` are compared after both are coerced to UTC,
because SQLite hands back naive datetimes while PostgreSQL keeps the
offset.

## Seal geometry

The seal is `min(150vw, 1400px)`: one declaration rather than a base value
plus a desktop override, so nothing depends on which rule wins.

The label and title must sit on the seal's flat body, never on the toothed
rim. In the drawing the flat body ends at radius 249 of a 600 unit box and
the teeth reach 296.4, so the body's top edge is `0.085 × diameter` below
the seal's top. A fixed `rem` offset cannot track that, because the edge
moves down as the seal grows; the cap is therefore placed at
`--cap-offset × --seal-size` below the seal top. The chord of a circle is
narrowest at the top of a text box and widens below it, so fitting the
first line inside the body keeps the whole block inside.

The teeth are not outside the body: they are circles of radius 34.2
centred at radius 262.2, so they reach inwards to 228, well inside the
body's own 249. The safe radius for text is therefore 228, not 249, and an
earlier version that kept the text inside 249 was already clipping the
rim.

The band height follows from the same numbers rather than being a fixed
figure: seal top, plus the cap offset, plus room for the text and the
card's overlap. It is computed from the sealed seal position only, so
breaking the seal does not resize the band mid-animation.

What bounds the sizes is not the drawing but the fold: on a 390x844 phone
and a 1366x768 laptop the clue, the tiles and the assist buttons have to
be visible without scrolling, and the Turkish keyboard still has to fit
underneath. Because the text's required depth grows with the seal, a
larger seal costs band height directly, so the seal is capped at 1100px
and drops to 900px from 1024px up, where the viewport is usually shortest.

Measured in a browser: the label and title glyphs stay at or below 0.892
of the body radius, inside the 0.916 where the teeth begin, and clear the
card by 13 to 17px. The assist buttons end 246px above the fold on the
phone and 67px above it on the laptop; the keyboard will take the text
input's place, which returns about 60px more.

## Stacking order

The band does not create a stacking context, so its layers and the card
are ordered in one place: band wash and seal at 0, the date and the seal
cap at 1, the page container at 2, the header at 3 and the menu panel
at 4. The card has to be above the seal, since it overlaps the band, while
the header and its menu have to be above the card, since the menu opens
downwards over it. Giving the band its own stacking context would force a
choice between those two.

## Result window

The window is a native `<dialog>` opened with `showModal()`, which gives
Esc, the focus trap and focus restoration without code; the close button
is a `<form method="dialog">` submit, so it works even if the module fails
to load. A click whose target is the dialog itself is a backdrop click and
closes it.

Revealing the answer asks first, in a dialog built from the same panel
rather than the browser's `confirm()`, which cannot be styled and reads as
a browser warning. The buttons are a `<form method="dialog">` submit each,
so the choice arrives as `returnValue`: Esc and a backdrop click leave it
empty and therefore count as cancelling, and focus starts on "Vazgeç". The
note names the real cost, which differs by puzzle: the daily puzzle
resets the streak, while a practice or archive puzzle only stops counting
as solved.

The lock that holds the controls during the solve scene is scoped to the
guess form and the assist buttons. It once covered every button inside the
card, which silently disabled the confirm dialog's own buttons while the
scene flag was set.

It opens by itself only when the puzzle is finished in front of the
player. A finished puzzle's page is rendered with the numbers already in
place and marked `data-ready="1"`, which turns on the "Sonucu göster"
button instead, so a reload never replays the moment. Both paths write the
same fields: the server from the play record, the client from the
guess or reveal response, which now also carries guess, hint and letter
counts.

## Animation

Only transform and opacity are animated, so the phone stays smooth. Three
effects would naturally have been colour animations and were rebuilt:

- The band's navy to turquoise change is a cross-fade. A `.band-wash`
  layer painted with the sealed colour sits over the band background and
  fades out while the state flips underneath. The seal itself swaps at
  that instant rather than fading, since cross-fading it would mean
  drawing it twice.
- The definition highlight fills from the left by scaling a pseudo-element
  on the X axis, not by animating a clip or a colour.
- A wrong guess flashes a red ring drawn as a pseudo-element whose opacity
  animates, leaving the tile's own border untouched.

The solve scene runs about two seconds: tiles flip in turn, then the seal
breaks while the band cross-fades, then the solution rises and the streak
turns over. Revealing the answer plays the same scene without the tile
flips. A single `busy` flag holds the whole scene, so a second click
cannot start it or the window twice.

`motionOk()` is checked in one place. Under
`prefers-reduced-motion: reduce` nothing animates: the final state is
applied at once and the window opens plainly. The stylesheet's global
reduced-motion rule covers the CSS keyframes.

The game script is split into `motion.js`, `result.js` and `game.js` and
loaded as an ES module, which keeps the files small without any inline
script; modules load from the same origin, so the CSP is unchanged.

## Opening letters

"Harf aç" opens a random position rather than the next one from the left,
which made every puzzle start the same way. The order is not stored: it is
derived from the player id and the puzzle id with a sha256 digest fed to
`random.Random`, so it is the same on every request and usually differs
between players. Python's `hash()` would not do, since it is salted per
process and would hand the same player different letters after a restart.

The order covers every position except the last, so "the last letter never
opens" is a property of the sequence rather than a check somewhere. The
API's existing stop at one letter short of the answer still holds.

`tile_groups` and `letter_pattern` take the set of open positions instead
of a count, which leaves word breaks alone for multi-word answers. The
letter endpoint returns the position it opened so the client flips the
right tile instead of guessing which one is new.

The position is derived from the player object rather than `play.player_id`
inside the endpoint: a play created in that same request has no id on the
foreign key column until the session is flushed, which silently gave every
new player the same order.

## Difficulty and time chips

Two chips sit above the clue on every puzzle. The clock starts when the
page is first opened, from the same session timestamp as the solve time,
and the server sends the seconds already elapsed so a reload continues
instead of restarting. The client only increments a number it was given.

For this to hold, `mark_opened` now keeps an existing timestamp instead of
writing a new one on every render. Before, reloading the page restarted
the clock, which also made the solve time shorter than it really was.

When a puzzle finishes, the counter stops and is set to the duration from
the API response, so the chip and the result window can never disagree.
A finished puzzle's page renders the final figure with the counter already
stopped. Both sides format the same way: `dk:sn`, or `sa:dk:sn` past an
hour.

## Community line

The result window carries one line about everyone who solved the puzzle:
the mean guess count and the median time. The mean is the fair summary of
guesses, but time needs the median, because a player who leaves the tab
open for an afternoon would drag an average far past anything a person
recognises.

Fewer than twenty solvers and the line is left out rather than shown with
a caveat; a handful of people is not a crowd. No solve percentage is
shown: it reads as a grade on the player rather than a fact about the
puzzle.

Only solved plays count. Revealed answers say nothing about how long
solving takes, and unfinished plays have no time at all.

The figures are cached per puzzle for five minutes in the Redis the rate
limiter already uses, so no new service or setting appears. Without Redis
the numbers are simply computed, and any Redis error falls back the same
way — the same rule as rate limits, where an outage must not take the
site down. The line itself is built outside the cache, so the daily
puzzle's wording switches from "Bugün çözenler" the moment its day ends.

The median is computed in Python. `percentile_cont` would push it into the
database, but it is PostgreSQL-only and the tests run on SQLite.

## The week's hard puzzle

A daily puzzle published on a Sunday is the week's hard one. Nothing is
stored for this: the rule reads the publish date, so no column, no
migration, and no way for the flag to disagree with the calendar.

The admin dashboard marks Sundays and warns about any Sunday in the next
two weeks that is empty or not set to "Zor". Saving an easy Sunday puzzle
is still allowed and only adds a notice: the warning is about planning the
schedule, and blocking the save would stop an editor fixing a typo on a
puzzle whose difficulty someone else has to decide.

## Stats in a window

The stats page became a dialog opened from the header and the phone menu,
built from the same panel as the result window, so a player checking their
streak no longer leaves the puzzle. The numbers arrive from `/api/me/stats`
when the window opens rather than being rendered into every page, which
keeps them off pages that do not need them, and reading them creates no
player row.

`/istatistik` answers 301 to the home page, since the address has been
linked and indexed.

## Publishing from the admin

A draft goes live with one button in the list, the calendar and the edit
page. The checks live in `publish_problem` rather than in the form's
`save_puzzle`: the form only re-checks a date when it changes, which is
right for editing but wrong here, because a draft can sit untouched until
its day has passed.

The "date already taken" branch cannot actually be reached for a stored
puzzle, since `publish_date` is unique in the database; it stays as a
guard in case that ever loosens, and the test records why instead of
pretending to exercise it.

The buttons carry a `back` field checked against a fixed list rather than
following `request.referrer`, for the same reason the login page ignores
`next`: a referrer is attacker-controlled and would be an open redirect.

Pulling a puzzle back to draft is refused once it is published or played,
which is the same lock that already protects its answer and date.

## Guide and glossary

The guide's text, indicator words and worked examples live in
`muamma/guide.py` as plain data, and both the guide page and the in-game
glossary render from it. Editing the content means editing one file, and
the two can never drift apart. Each clue is stored as a list of runs, so
every part carries its own role and the template never has to search the
sentence for substrings to colour.

The tabs are built by JavaScript from sections that are already in the
markup. Rendering a tablist server-side would leave dead buttons when the
module fails to load; this way the page is three readable sections and the
script only upgrades them, adding the roles, arrow-key movement and
selection state.

The anatomy parts are `<button>` elements. A span with a mouse handler
would need extra work for touch and keyboard; a button gets all three, and
`aria-describedby` ties each part to its explanation.

Inside the glossary's search field the first Escape is swallowed by the
browser to undo the typing, so the field closes the dialog itself. Escape
then means the same thing in every window.

Colour alone never says which part is which: each one is labelled in
words next to it, for the same reason the tiles have a hidden text
pattern.

## Dropped features

The Turkish on-screen keyboard, the indicator and fodder highlights with
their legend, the par chip and the "guesses / par" box, the step-by-step
solution built from those highlights, and the community solve rate were
all dropped and removed from docs/design.md. The clue keeps its definition
highlight and the finished puzzle keeps the explanation the setter wrote.

## Guess input

The input accepts letters only and never more than the answer holds. The
limit is rendered by the server as both `maxlength` and a data attribute,
so it always matches the puzzle rather than a number kept in the client.
Filtering happens on the `input` event, which also fires after a paste, so
a pasted string is stripped and truncated like typing. None of this
replaces the server's own length check; it only keeps the player from
typing something that could not be right.

A wrong guess shakes the tiles, flashes a red ring, and then drops the
typed letters out of their tiles one after another before clearing the
field. Focus stays in the input so the next attempt can start
immediately. Revealed letters stay put, since they are not what was
wrong.

The letters sit in their own span inside each tile: animating the tile
itself would drop the box out of the grid. Because a tile now always has
a child, the fill styling moved from `:not(:empty)` to a class the
template and the client both set. If the player types while the letters
are still falling, the drop is cancelled first, so the new letters are not
left invisible under a finished animation.

## Wrong guesses

Wrong guesses are read back from the event log for this player and puzzle,
oldest first, so a reload restores them like every other piece of
progress. The correct guess is filtered out in Python rather than with a
JSON query, to stay portable across SQLite and PostgreSQL over what is a
handful of rows per player and puzzle.

## Phone menu

The header menu is a `<details>`/`<summary>` disclosure, not a scripted
dropdown: it is keyboard accessible, needs no JavaScript at all and so
raises no CSP question. The panel would be cut off by the band, which
clips the oversized seal, so the clipping moved to a `.seal-layer` inside
the band instead of the band itself.

The footer keeps the same links regardless, so every page is reachable
without opening the menu.

## Comparison page

`/minute-cryptic-turkce` answers a question people actually search for.
It states plainly that the other game is English-only and has no Turkish
version, explains what Muamma is, and shows with a Turkish example why
cryptic clues cannot be translated: the wordplay depends on the letters of
the answer, so a translated clue keeps its meaning and loses its game.

The other game's name appears only in descriptions of it, never as a
product name of ours, and the page closes by stating that Muamma is not
affiliated with it and that the name and brand belong to their owners.

**Removed.** The page is gone, and with it the route, the template, the
sitemap entry and the footer link; the address now answers 404. Whatever
the page was worth in search, we would rather not talk about another
product on our own site. The name appears nowhere on it any more, and a
test walks the pages to keep it that way.

## The palette

Turquoise is gone. The game is warm paper, ink and a cobalt seal: a page
of `#F7F2EB`, a card of `#FFF9F0`, `#081F5C` for every word, and `#334EAC`
for the wax. The values come from the three reference pages in
`docs/palet-referans/`, applied to the existing tokens rather than copied
as markup.

The seal is a radial gradient lit from the upper left, and its stops are
set in the stylesheet rather than on the SVG, so one piece of markup
serves both themes and both states. The whole seal and the broken one
carry different gradient ids, since both sit on the same page.

One value departs from the reference: the gradient's middle stop moves
from 0.45 to 0.25. At 0.45 the "MÜHÜRLÜ" label — small bold text on the
light part of the wax — came to 3.75:1 on phones and 4.14:1 on desktop,
short of the 4.5:1 it needs. Moving the stop keeps all three colours and
the light's direction, darkens the wax under the cap, and brings the label
to 4.68:1 and 5.65:1. The title, which is large text, passes either way.

Everything else clears AA as drawn, with `#7096D1` used only as a surface,
never as a text colour, and `#FFF9F0` rather than navy wherever text sits
on the seal.

The grain is one fixed layer over the viewport and one over the band, so
scrolling never repaints a document-tall texture, and neither takes
pointer events. The admin is excluded: it takes the colours and nothing
else, because it is a tool and the texture would only be in the way.

## The definition highlight on a wrapped line

The highlight used to be a `::before` with `position: absolute; inset: 0`.
On one line that is fine; on two it is one rectangle stretched over the
whole inline fragment, covering the gap between the lines and running past
the end of the shorter one. A multi-word definition on a phone looked
pasted on at an angle.

It is now the text's own background with `box-decoration-break: clone`, so
every line fragment gets its own padding, corners and fill. The same goes
for the three marked parts in the guide, which wrap the same way.

The ink that fills from the left is therefore an animated
`background-size` rather than a transform. **This is the one place the
"only transform and opacity" rule is broken**, and it has to be: a
transform scales the whole element, so on a wrapped definition it would
sweep across both lines from the first line's left edge instead of filling
each line from its own. The animation touches a single small inline
element and runs once per hint. Under `prefers-reduced-motion` it does not
run at all.

## Keeping the tiles centred

Three things were wrong at once, all found in the browser.

The row is left-aligned only while it overflows, so the start stays
reachable. But a row could overflow by as little as seven pixels and still
flip the whole thing to the left, which reads as a centring bug rather
than as scrolling. The gaps between tiles now close from 4px to 2px once
the tiles are already at their 20px floor, which is enough to fit twelve
letters at 360px and fifteen at 430px. What still scrolls genuinely cannot
fit.

Width changes that did not come from the window were missed entirely: only
`resize` was listened for, so a card that narrowed for any other reason
left the tiles at their old size and overflowing without the scroll hint.
A `ResizeObserver` on the row catches all of it.

The first measurement also runs before the web fonts have settled, so
`document.fonts.ready` triggers one more pass. Nothing in the size
calculation depends on the fonts today, but it is a cheap guard against a
late reflow leaving a stale measurement behind.

Measured at 320, 360, 390 and 430px across single and multi-word answers
of three to fifteen letters: every row that fits is centred to the pixel,
wrapped word groups included.

## The browser's hidden rule

Setting `hidden` on the guess form and the assists did nothing: an author
`display: flex` outranks the browser's own `[hidden] { display: none }`,
so both stayed on screen after a puzzle was finished, including on a
reloaded page. A `[hidden] { display: none !important }` reset fixes it
for every element at once. It had been wrong since the stylesheet was
rewritten; a screenshot of the solved state is what showed it.

## Fitting the tiles on a phone

The tile row is a block with the word groups as inline-flex boxes, and
each tile's size comes from a custom property that `game.js` sets from the
measured row width and the longest word. The obvious CSS-only version —
shrinkable flex items with a `min-width` floor — does not work: when a
group asks for its max-content width, Chrome sizes a shrinkable flex item
from its `min-width` rather than its `flex-basis`, so every tile collapsed
to the floor at every screen size, desktop included. Measuring and setting
the size is both simpler to reason about and immune to that.

Measured sizes, phone cap 54px and desktop cap 66px:

| Answer | 320 | 360 | 390 | 430 | 768 | 1366 |
|---|---|---|---|---|---|---|
| 3 letters | 54 | 54 | 54 | 54 | 54 | 66 |
| 5,5,5 | 43.6 | 51.6 | 54 | 54 | 54 | 66 |
| 15 letters | 20* | 20* | 20* | 20* | 35.9 | 39.6 |

\* at the 20px floor, where the row scrolls inside the card.

Below 20px a tile is not worth looking at, so the row scrolls instead,
with a fading right edge and a thin scrollbar. The page never scrolls
sideways at any width. Word groups wrap as units, so a word is never
split; only a single word too long for the floor reaches the scrolling
case.

The row keeps `overflow-x: auto` at all times, which also saves a reader
without JavaScript from a sideways page, and carries enough vertical
padding that the solved bounce above and the falling letters below are not
clipped by it.

The admin form warns when a word is longer than twelve letters. It does
not block saving: the setter may have a good reason, and the warning is
there so the tile size is a decision rather than a surprise.

## Reading pages

The guide, "Muamma nedir?", privacy and the archive carry a `reading`
class on `<body>` and get their own wider, airier column. They were
sharing the game's 680px, which is right for a card with a clue and tiles
and wrong for prose: too long and thin on a desktop, too cramped on a
phone. The game's own layout is untouched.

## The result window celebrates

Solving plays about 1.2 seconds: a spring entrance, a hop and tilt on the
cat, a dozen drops of sealing wax thrown from behind it, the title arriving
word by word, the numbers counting up, and one pulse on the share button a
second in. Only transform and opacity are animated.

The drops are created in JavaScript and removed in a `finally`, so a
cancelled or interrupted animation cannot leave anything behind in the
page.

Revealing the answer opens the same window plainly. The celebration is for
solving; firing it after someone gives up would read as mockery. Under
`prefers-reduced-motion` none of it runs and the window simply appears.

## Practice by type

Each guide type names the stored `technique` it corresponds to, on the
type itself rather than in a separate mapping table. A second structure
would be a second place to forget when a type is added.

The guide asks the database once which techniques have a ready practice
puzzle and only shows the button for those. It does not ask whether this
player has finished them: the page would then differ per reader for no
gain, and the redirect already copes with a player who has solved them
all.

`/tadimlik?teknik=` keeps no list of valid values. An unknown technique
matches no row, so the query comes back empty and the route falls back to
any practice puzzle. The same fallback covers a real technique whose
puzzles the player has already finished, and there is no list to drift out
of step with the guide.

The admin's technique list gained the six types it was missing. The
stored values of the existing ones are untouched, since puzzles carry them
in the database. "Harf adları" was added next to the older "Sesteş"
rather than replacing it: renaming a stored value would orphan the
puzzles filed under it, and the two are not quite the same thing.

## "Muamma nedir?" page

The story of the name moved out of the guide and onto its own page, which
also explains what the game is and how its week runs. The guide now points
at it in one line: the guide is for learning to solve, and a history
lesson in the middle of it was in the way.

Its text lives in the template rather than in a data module like
`muamma/guide.py`. That module exists because two views, the guide page
and the glossary, have to render the same content and must not drift; this
page has one reader, and its prose and layout are written together.

The glossary button was taken off the day's puzzle at the same time. On
practice and archive puzzles a list of indicators is a study aid; on the
one puzzle everybody solves together it is a crib sheet.

The page later lost its "what we care about" and FAQ sections. Both said
again, in marketing voice, what the privacy page already says plainly and
has to keep saying to stay accurate; two places telling the same story is
one place too many to keep true. With the FAQ went the only use of
`CONTACT_EMAIL` on this page, so the route stopped passing it — the
address now appears on the privacy page alone, where deletion requests
belong.

The privacy page dropped its own opening section for the same reason: it
described the cookie that the cookie section describes. The facts that
only lived there — that the player id is made on the first guess, that it
remembers the streak and the stats, and that it holds nothing about the
player — moved into the cookie section rather than being lost.

## Privacy page

The privacy page describes what the code actually stores: one session
cookie with an anonymous player id and CSRF token, gameplay events tied
to that id, and IP addresses only inside short-lived rate limit counters.
It is not a legal review; KVKK obligations should be checked before
launch.