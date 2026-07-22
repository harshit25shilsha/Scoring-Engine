from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings


def to_mysql_naive(dt: datetime) -> datetime:
    local_tz = ZoneInfo(settings.MYSQL_TIMEZONE)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(local_tz).replace(tzinfo=None)