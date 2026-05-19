from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta
from typing import Optional, Tuple

import pytz

from config import MARKET_CLOSE, MARKET_OPEN, NSE_HOLIDAYS, TIMEZONE

_TZ = pytz.timezone(TIMEZONE)
_HOLIDAYS = {
    datetime.strptime(day, "%Y-%m-%d").date() for day in NSE_HOLIDAYS
}


def is_market_open(now: Optional[datetime] = None) -> bool:
    is_open, _, _ = get_market_status(now)
    return is_open


def get_market_status(
    now: Optional[datetime] = None,
) -> Tuple[bool, str, Optional[datetime]]:
    current = _coerce_now(now)
    open_time = _parse_time(MARKET_OPEN)
    close_time = _parse_time(MARKET_CLOSE)

    open_dt = current.replace(
        hour=open_time.hour,
        minute=open_time.minute,
        second=0,
        microsecond=0,
    )
    close_dt = current.replace(
        hour=close_time.hour,
        minute=close_time.minute,
        second=0,
        microsecond=0,
    )

    if _is_holiday(current):
        next_open = _next_market_open(current + timedelta(days=1))
        return False, f"Holiday on {current.date()}", next_open

    if _is_weekend(current):
        next_open = _next_market_open(current + timedelta(days=1))
        return False, "Weekend", next_open

    if current < open_dt:
        return False, "Market not open yet", open_dt

    if current > close_dt:
        next_open = _next_market_open(current + timedelta(days=1))
        return False, "Market closed for the day", next_open

    return True, "Market is open", None


def now_ist() -> datetime:
    return datetime.now(_TZ)


def _coerce_now(now: Optional[datetime]) -> datetime:
    if now is None:
        return now_ist()
    if now.tzinfo is None:
        return _TZ.localize(now)
    return now.astimezone(_TZ)


def _parse_time(value: str) -> dt_time:
    hour_str, minute_str = value.split(":")
    return dt_time(hour=int(hour_str), minute=int(minute_str))


def _is_weekend(current: datetime) -> bool:
    return current.weekday() >= 5


def _is_holiday(current: datetime) -> bool:
    return current.date() in _HOLIDAYS


def _next_market_open(start: datetime) -> datetime:
    candidate = _coerce_now(start)
    open_time = _parse_time(MARKET_OPEN)

    while True:
        if not _is_weekend(candidate) and not _is_holiday(candidate):
            return candidate.replace(
                hour=open_time.hour,
                minute=open_time.minute,
                second=0,
                microsecond=0,
            )
        candidate += timedelta(days=1)
