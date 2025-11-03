import os, time
import pandas as pd
from datetime import datetime, timedelta, timezone
from loguru import logger
from pybit.unified_trading import HTTP
from .config import SETTINGS

# Bybit v5 erwartet Minuten als String (z. B. "5" statt "5m")
INTERVAL_MAP = {"1m":"1","3m":"3","5m":"5","15m":"15","30m":"30","60m":"60","120m":"120","240m":"240"}

def _http_session():
    # Public Kline braucht keine Auth, Keys sind ok aber optional
    return HTTP(timeout=60,  testnet=bool(SETTINGS.bybit_testnet),
        api_key=SETTINGS.bybit_api_key or None,
        api_secret=SETTINGS.bybit_api_secret or None,
    )

def _ts_ms(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)

def backfill(symbol: str, timeframe: str, lookback_days: int = 2) -> pd.DataFrame:
    """Ziehe historische Klines via /v5/market/kline (Kategorie 'linear' für USDT-Perps)."""
    interval = INTERVAL_MAP.get(timeframe, "5")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)

    sess = _http_session()
    all_rows = []
    cursor_start = start

    # Safety: Max 10 Iterationen, damit wir nie "endlos" hängen
    max_iters = 10
    iters = 0

    while cursor_start < end and iters < max_iters:
        iters += 1
        logger.info("Kline-Request #{}, {} → {}", iters, cursor_start.isoformat(), end.isoformat())

        try:
            resp = sess.get_kline(
                category="linear",
                symbol=symbol,
                interval=interval,
                start=_ts_ms(cursor_start),
                end=_ts_ms(end),
                limit=500,  # kleiner halten
            )
        except Exception as e:
            logger.error(f"HTTP-Fehler bei get_kline: {e}")
            break

        if resp.get("retCode") != 0:
            logger.error(f"Bybit get_kline error: {resp}")
            break

        lst = resp["result"].get("list", [])
        logger.info("Kline-Request #{}: erhalten {} Zeilen", iters, len(lst))

        if not lst:
            break

        for row in lst:
            ts = int(row[0])
            all_rows.append({
                "ts": datetime.fromtimestamp(ts/1000, tz=timezone.utc),
                "open": float(row[1]),
                "high": float(row[2]),
                "low":  float(row[3]),
                "close":float(row[4]),
                "volume": float(row[5]),
            })

        last_ts = int(lst[-1][0])
        cursor_start = datetime.fromtimestamp(last_ts/1000, tz=timezone.utc) + timedelta(milliseconds=1)
        time.sleep(0.1)  # sanftes Rate-Limit

    if not all_rows:
        logger.warning("Kein Kline-Backfill erhalten ({} Iterationen).", iters)
        return pd.DataFrame()

    df = pd.DataFrame(all_rows).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    return df