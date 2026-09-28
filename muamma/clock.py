from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from flask import current_app


def now() -> datetime:
    """Current time in the app timezone."""
    return datetime.now(ZoneInfo(current_app.config["APP_TIMEZONE"]))


def today() -> date:
    return now().date()


def seconds_until_tomorrow() -> int:
    current = now()
    midnight = datetime.combine(current.date() + timedelta(days=1), time.min, current.tzinfo)
    return max(int((midnight - current).total_seconds()), 0)