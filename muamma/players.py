import uuid

from flask import session
from flask_limiter.util import get_remote_address

from muamma.extensions import db
from muamma.models import Player, utcnow

SESSION_KEY = "player_id"


def current_player(create: bool = False) -> Player | None:
    """Player bound to this browser session; created only when asked."""
    player = None
    raw = session.get(SESSION_KEY)
    if raw:
        try:
            player = db.session.get(Player, uuid.UUID(raw))
        except ValueError:
            player = None

    if player is None and create:
        player = Player(current_streak=0, max_streak=0)
        db.session.add(player)
        db.session.flush()
        session[SESSION_KEY] = str(player.id)
        session.permanent = True

    if player is not None and create:
        player.last_seen_at = utcnow()

    return player


def player_or_ip() -> str:
    """Rate-limit key: player id when known, otherwise client IP."""
    player_id = session.get(SESSION_KEY)
    return f"player:{player_id}" if player_id else f"ip:{get_remote_address()}"