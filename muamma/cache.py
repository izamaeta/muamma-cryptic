import json

from flask import current_app

_clients: dict[str, object] = {}


def _client():
    """Redis client shared with the rate limiter, or None when there is none."""
    uri = current_app.config.get("RATELIMIT_STORAGE_URI", "")
    if not uri.startswith(("redis://", "rediss://")):
        return None
    if uri not in _clients:
        try:
            import redis

            _clients[uri] = redis.Redis.from_url(uri, socket_timeout=0.5)
        except Exception:
            _clients[uri] = None
    return _clients[uri]


def cached(key: str, ttl: int, compute):
    """Compute the value, keeping it in Redis when one is configured.

    Any Redis trouble falls back to computing, the same way rate limits
    allow requests through rather than failing.
    """
    client = _client()
    if client is None:
        return compute()

    try:
        stored = client.get(key)
        if stored is not None:
            return json.loads(stored)
    except Exception:
        return compute()

    value = compute()
    try:
        client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass
    return value
