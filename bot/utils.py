from datetime import datetime, time
from zoneinfo import ZoneInfo
from .config import SETTINGS

def session_is_open(dt_utc: datetime) -> bool:
    if not SETTINGS.use_session:
        return True
    tz = ZoneInfo(SETTINGS.tz)
    local = dt_utc.astimezone(tz)
    start_h, start_m = map(int, SETTINGS.session_start.split(':'))
    end_h, end_m = map(int, SETTINGS.session_end.split(':'))
    start = time(start_h, start_m)
    end = time(end_h, end_m)
    return start <= local.time() <= end

def is_within_minutes_of_hour(dt_utc: datetime, minutes: int) -> bool:
    minute = dt_utc.minute
    return minute < minutes or minute > (60 - minutes)

def pct(a, b) -> float:
    if b == 0:
        return 0.0
    return (a / b) * 100.0

def clamp_qty_to_precision(qty: float, step: float) -> float:
    # simple precision clamp; in real broker, fetch lot size meta
    return round(qty / step) * step
