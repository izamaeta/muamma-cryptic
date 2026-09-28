from datetime import date, datetime
from zoneinfo import ZoneInfo

from flask import current_app


def today() -> date:
    """Current date in the app timezone."""
    tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
    return datetime.now(tz).date()