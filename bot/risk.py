from .config import SETTINGS

def should_timeout(bars_open: int) -> bool:
    return bars_open >= 50  # 50 Kerzen

def should_daily_stop(daily_dd_pct: float) -> bool:
    return daily_dd_pct <= -SETTINGS.daily_loss_limit_pct

def trail_params(unrealized_pnl_pct: float):
    if unrealized_pnl_pct >= SETTINGS.trail_trigger_pct:
        return True, SETTINGS.trail_distance_pct
    return False, None

def use_tp() -> bool:
    return SETTINGS.use_tp
