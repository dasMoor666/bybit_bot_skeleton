# --- stdlib ---
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Python 3.11+: stdlib

# --- 3rd party ---
from loguru import logger

# --- project ---
from .config import SETTINGS
from .data import backfill
from . import indicators as ind
from . import strategy as strat

# --- state (module-level) ---
# Verhindert doppelte Orders auf derselben Kerze
LAST_FILLED_BAR = {"LONG": None, "SHORT": None}


def _size_from_risk(entry: float, sl_pct: float, balance: float, risk_pct_pct: float) -> float:
    risk_amount = balance * (risk_pct_pct / 100.0)
    sl_dist = entry * (sl_pct / 100.0)
    if sl_dist <= 0:
        return 0.0
    qty = risk_amount / sl_dist
    return max(qty, 0.0)


def _fmt_price(p: float) -> str:
    return f"{p:.2f}"


def _in_session(now_local: datetime) -> bool:
    if not SETTINGS.use_session:
        return True
    start_h, start_m = map(int, SETTINGS.session_start.split(":"))
    end_h, end_m = map(int, SETTINGS.session_end.split(":"))
    start = now_local.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end = now_local.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    return start <= now_local <= end


def main():
    # ---------- Logging ----------
    logger.remove()
    logger.add(sys.stderr, level=SETTINGS.loguru_level.upper())

    logger.info("Start Bot-Loop (DRY_RUN={})  Symbol={} TF={}", SETTINGS.dry_run, SETTINGS.symbol, SETTINGS.timeframe)

    tz = ZoneInfo(SETTINGS.tz)
    balance = getattr(SETTINGS, "start_balance", 10_000.0)  # DRY_RUN Startsaldo
    sl_pct = SETTINGS.sl_pct
    tp_pct = SETTINGS.tp_pct

    # Rate-Limit: max neue Entries pro Stunde
    hour_bucket_start = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
    new_entries_this_hour = 0

    # Hauptloop
    while True:
        now_local = datetime.now(tz)

        # Stunde gewechselt? Zähler zurücksetzen
        if now_local >= hour_bucket_start + timedelta(hours=1):
            hour_bucket_start = now_local.replace(minute=0, second=0, microsecond=0)
            new_entries_this_hour = 0

        if not _in_session(now_local):
            logger.debug("Außerhalb Session {}–{} {} – schlafe 60s", SETTINGS.session_start, SETTINGS.session_end, SETTINGS.tz)
            time.sleep(60)
            continue

        # ---------- Backfill + Indikatoren ----------
        logger.debug("Backfill ...")
        df = backfill(SETTINGS.symbol, SETTINGS.timeframe, lookback_days=2)
        rows = 0 if df is None else len(df)
        if rows < 100:
            logger.warning("Zu wenig Daten ({}) – schlafe 60s", rows)
            time.sleep(60)
            continue

        df = ind.compute_all(df)

        # ---------- Signalprüfung nur auf der letzten Kerze ----------
        row_prev = df.iloc[-2]
        row_now = df.iloc[-1]
        spread_pct = SETTINGS.max_spread_pct if hasattr(SETTINGS, "max_spread_pct") else 0.02

        long_ok = strat.long_signal(row_now, row_prev, spread_pct)
        short_ok = strat.short_signal(row_now, row_prev, spread_pct)

        long_count = 1 if long_ok else 0
        short_count = 1 if short_ok else 0

        logger.info("Signals (letzte Kerze): LONG={}, SHORT={}", long_count, short_count)

        # ---------- Entry-Rate-Limit ----------
        if new_entries_this_hour >= SETTINGS.max_new_entries_per_hour:
            logger.info("Rate-Limit erreicht ({} neue Entries/h). Keine neuen Orders in dieser Stunde.",
                        SETTINGS.max_new_entries_per_hour)
            time.sleep(60)
            continue

        # ---------- DRY_RUN Orders simulieren ----------
        simulated = 0
        if SETTINGS.dry_run:
            if long_ok and new_entries_this_hour < SETTINGS.max_new_entries_per_hour:
                entry = float(row_now["close"])
                qty = _size_from_risk(entry, sl_pct, balance, SETTINGS.risk_per_trade_pct)
                sl = entry * (1.0 - sl_pct / 100.0)
                tp = entry * (1.0 + tp_pct / 100.0) if SETTINGS.use_tp else None
                logger.info("[DRY_RUN] LONG {} qty={:.6f} entry={} SL={}{}",
                            SETTINGS.symbol, qty, _fmt_price(entry), _fmt_price(sl),
                            f" TP={_fmt_price(tp)}" if tp else "")
                simulated += 1
                new_entries_this_hour += 1

            elif short_ok and new_entries_this_hour < SETTINGS.max_new_entries_per_hour:
                entry = float(row_now["close"])
                qty = _size_from_risk(entry, sl_pct, balance, SETTINGS.risk_per_trade_pct)
                sl = entry * (1.0 + sl_pct / 100.0)
                tp = entry * (1.0 - tp_pct / 100.0) if SETTINGS.use_tp else None
                logger.info("[DRY_RUN] SHORT {} qty={:.6f} entry={} SL={}{}",
                            SETTINGS.symbol, qty, _fmt_price(entry), _fmt_price(sl),
                            f" TP={_fmt_price(tp)}" if tp else "")
                simulated += 1
                new_entries_this_hour += 1

        # ---------- Status ----------
        last = df.iloc[-1]
        logger.info("Letzte Kerze: {} O:{} H:{} L:{} C:{} Vol:{} | Simuliert: {} | Neue Entries diese Stunde: {}",
                    last["ts"], last["open"], last["high"], last["low"], last["close"], last["volume"],
                    simulated, new_entries_this_hour)

        # Herzschlag
        sleep_s = max(SETTINGS.heartbeat_secs, 15)
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()