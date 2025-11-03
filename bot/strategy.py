from loguru import logger
import os
import pandas as pd
from typing import List, Tuple
from dotenv import load_dotenv
load_dotenv()

# === Laufzeit-Flags aus ENV ===
ALLOW_CONT = os.getenv("ALLOW_CONTINUATION", "true").lower() in ("1", "true", "yes")
DEBUG_SIGNALS = os.getenv("DEBUG_SIGNALS", "false").lower() in ("1", "true", "yes")

logger.info(f"Continuation-Trading erlaubt: {ALLOW_CONT}")

# === Parameter aus ENV (mit soften Defaults) ===
VOL_MULT_BASE = float(os.getenv("VOL_MULT_BASE", "1.0"))   # Volume-Multiplikator ggü. vol_sma
ATR_MIN       = float(os.getenv("ATR_MIN", "0.01"))        # minimaler ATR% (volatil genug?)
ATR_MAX       = float(os.getenv("ATR_MAX", "6.0"))         # maximaler ATR%
RSI_LONG_MIN  = float(os.getenv("RSI_LONG_MIN", "45"))
RSI_LONG_MAX  = float(os.getenv("RSI_LONG_MAX", "75"))
RSI_SHORT_MIN = float(os.getenv("RSI_SHORT_MIN", "25"))
RSI_SHORT_MAX = float(os.getenv("RSI_SHORT_MAX", "55"))

# --------------------------------------------------------------------------- #
#                              Hilfsfunktionen                                #
# --------------------------------------------------------------------------- #

def _valid_row(row: pd.Series) -> bool:
    needed = ["ema_fast", "ema_slow", "rsi", "atr_pct", "volume", "vol_sma", "close"]
    return all(k in row and pd.notna(row[k]) for k in needed)

def _passes_filters(row: pd.Series, side: str) -> bool:
    """Volumen/ATR/RSI-Filter; gibt True zurück, wenn alle Filter ok sind.
       Neu: Optionaler Continuation-Override beim RSI (ALLOW_CONT).
    """
    # --- Volumen-Filter (wenn vol_sma fehlt → bestehen lassen) ---
    vol_sma = row.get("vol_sma", float("nan"))
    if pd.notna(vol_sma):
        if row["volume"] < vol_sma * VOL_MULT_BASE:
            if DEBUG_SIGNALS:
                logger.debug("[{}] Drop: volume {} < vol_sma*mult {}*{}",
                             side, row["volume"], vol_sma, VOL_MULT_BASE)
            return False
    vol_ok = True  # an dieser Stelle bereits bestanden, oder vol_sma fehlte

    # --- ATR-Band (wenn atr_pct fehlt → bestehen lassen) ---
    atr = row.get("atr_pct", float("nan"))
    if pd.notna(atr):
        if not (ATR_MIN <= atr <= ATR_MAX):
            if DEBUG_SIGNALS:
                logger.debug("[{}] Drop: atr_pct {} not in [{}, {}]", side, atr, ATR_MIN, ATR_MAX)
            return False
    atr_ok = True  # bestanden oder nicht vorhanden

    # --- RSI mit optionaler Continuation-Ausnahme ---
    rsi = row.get("rsi", float("nan"))

    # Trendflags für Continuation
    ema_fast = row.get("ema_fast", float("nan"))
    ema_slow = row.get("ema_slow", float("nan"))
    trend_up   = pd.notna(ema_fast) and pd.notna(ema_slow) and (ema_fast > ema_slow)
    trend_down = pd.notna(ema_fast) and pd.notna(ema_slow) and (ema_fast < ema_slow)

    if side == "LONG":
        if pd.notna(rsi) and not (RSI_LONG_MIN <= rsi <= RSI_LONG_MAX):
            # Continuation-Override nur, wenn erlaubt und eindeutig Momentum nach oben
            if ALLOW_CONT and trend_up and rsi > RSI_LONG_MAX and atr_ok and vol_ok:
                if DEBUG_SIGNALS:
                    logger.debug("[LONG] RSI continuation override: rsi {} > {} (trend_up, ALLOW_CONT)", rsi, RSI_LONG_MAX)
            else:
                if DEBUG_SIGNALS:
                    logger.debug("[LONG] Drop: rsi {} not in [{}, {}]", rsi, RSI_LONG_MIN, RSI_LONG_MAX)
                return False

    if side == "SHORT":
        if pd.notna(rsi) and not (RSI_SHORT_MIN <= rsi <= RSI_SHORT_MAX):
            # Symmetrischer Continuation-Override nach unten
            if ALLOW_CONT and trend_down and rsi < RSI_SHORT_MIN and atr_ok and vol_ok:
                if DEBUG_SIGNALS:
                    logger.debug("[SHORT] RSI continuation override: rsi {} < {} (trend_down, ALLOW_CONT)", rsi, RSI_SHORT_MIN)
            else:
                if DEBUG_SIGNALS:
                    logger.debug("[SHORT] Drop: rsi {} not in [{}, {}]", rsi, RSI_SHORT_MIN, RSI_SHORT_MAX)
                return False

    return True

# --------------------------------------------------------------------------- #
#                               Signal-Logik                                  #
# --------------------------------------------------------------------------- #

def long_signal(row_now: pd.Series, row_prev: pd.Series, spread_pct: float) -> bool:
    """Bullisches Signal: Cross oder (optional) Continuation bei Trendverstärkung."""
    if not (_valid_row(row_now) and _valid_row(row_prev)):
        return False

    # Cross- oder (falls erlaubt) Continuation-Setup
    trend_up_now  = row_now["ema_fast"] > row_now["ema_slow"]
    trend_up_prev = row_prev["ema_fast"] > row_prev["ema_slow"]
    gap_now  = row_now["ema_fast"] - row_now["ema_slow"]
    gap_prev = row_prev["ema_fast"] - row_prev["ema_slow"]

    if ALLOW_CONT:
        # a) frisch bestätigter Cross oder
        # b) laufender Uptrend und der Abstand nimmt zu (Trend-Stärkung)
        crossed_ok = ((row_prev["ema_fast"] <= row_prev["ema_slow"]) and trend_up_now) \
                     or (trend_up_now and gap_now > gap_prev)
    else:
        crossed_ok = (row_prev["ema_fast"] <= row_prev["ema_slow"]) and trend_up_now

    if not crossed_ok:
        return False

    if not _passes_filters(row_now, "LONG"):
        return False

    if DEBUG_SIGNALS:
        logger.debug("[LONG] OK @ {} close={}", row_now.get("ts", "?"), row_now["close"])
    return True

def long_signal(row_now, row_prev, max_spread_pct):
    # 0) Vorfilter
    if not _passes_filters(row_now, "LONG"):
        # logger.debug("[LONG] Drop: filters failed")
        return False

    # 1) Trend / Cross
    trend_up   = row_now.ema_fast > row_now.ema_slow
    cross_up   = (row_prev.ema_fast <= row_prev.ema_slow) and trend_up

    if cross_up:
        # logger.debug(f"[LONG] OK (fresh cross) @ {row_now.name} close={row_now.close}")
        return True

    # 2) Continuation (wenn erlaubt): Uptrend + expanding gap + Preis nicht schwach
    if ALLOW_CONT and trend_up:
        gap_prev = float(row_prev.ema_fast - row_prev.ema_slow)
        gap_now  = float(row_now.ema_fast - row_now.ema_slow)
        # kleine Hysterese: Lücke > 0 und wächst
        if gap_now > 0 and gap_now > gap_prev and row_now.close >= row_now.ema_fast:
            # logger.debug(f"[LONG] OK (continuation) @ {row_now.name} gap_prev={gap_prev:.2f} gap_now={gap_now:.2f}")
            return True
        # else:
            # logger.debug(f"[LONG] Drop (continuation conditions not met): gap_prev={gap_prev:.2f}, gap_now={gap_now:.2f}, close<{row_now.ema_fast:.2f}")

    return False


def short_signal(row_now, row_prev, max_spread_pct):
    if not _passes_filters(row_now, "SHORT"):
        return False

    trend_down = row_now.ema_fast < row_now.ema_slow
    cross_down = (row_prev.ema_fast >= row_prev.ema_slow) and trend_down

    if cross_down:
        return True

    if ALLOW_CONT and trend_down:
        gap_prev = float(row_prev.ema_slow - row_prev.ema_fast)
        gap_now  = float(row_now.ema_slow - row_now.ema_fast)
        if gap_now > 0 and gap_now > gap_prev and row_now.close <= row_now.ema_fast:
            return True

    return False


def short_signal(row_now: pd.Series, row_prev: pd.Series, spread_pct: float) -> bool:
    """Bärisches Signal: Cross oder (optional) Continuation bei Trendverstärkung."""
    if not (_valid_row(row_now) and _valid_row(row_prev)):
        return False

    trend_dn_now  = row_now["ema_fast"] < row_now["ema_slow"]
    trend_dn_prev = row_prev["ema_fast"] < row_prev["ema_slow"]
    gap_now  = row_now["ema_fast"] - row_now["ema_slow"]
    gap_prev = row_prev["ema_fast"] - row_prev["ema_slow"]

    if ALLOW_CONT:
        crossed_ok = ((row_prev["ema_fast"] >= row_prev["ema_slow"]) and trend_dn_now) \
                     or (trend_dn_now and gap_now < gap_prev)   # Abstand wird negativer → Trendverstärkung
    else:
        crossed_ok = (row_prev["ema_fast"] >= row_prev["ema_slow"]) and trend_dn_now

    if not crossed_ok:
        return False

    if not _passes_filters(row_now, "SHORT"):
        return False

    if DEBUG_SIGNALS:
        logger.debug("[SHORT] OK @ {} close={}", row_now.get("ts", "?"), row_now["close"])
    return True

# --------------------------------------------------------------------------- #
#                          Wrapper: komplette Suche                            #
# --------------------------------------------------------------------------- #

def generate_signals(df: pd.DataFrame) -> Tuple[List[dict], List[dict]]:
    """
    Liefert (longs, shorts) als Listen von Dicts:
      {'index': i, 'timestamp': df.index[i], 'side': 'LONG'/'SHORT', 'price': float(close)}
    Nutzt long_signal/short_signal(row_now, row_prev, spread_pct).
    """
    longs: List[dict] = []
    shorts: List[dict] = []

    if df is None or len(df) < 2:
        return longs, shorts

    spread_pct = 0.02  # Dummy-Spread für die Signallogik; reale Engine nutzt Settings

    for i in range(1, len(df)):
        row_prev = df.iloc[i - 1]
        row_now = df.iloc[i]

        try:
            if long_signal(row_now, row_prev, spread_pct):
                longs.append({
                    "index": i,
                    "timestamp": df.index[i],
                    "side": "LONG",
                    "price": float(row_now.get("close", float("nan"))),
                })
            if short_signal(row_now, row_prev, spread_pct):
                shorts.append({
                    "index": i,
                    "timestamp": df.index[i],
                    "side": "SHORT",
                    "price": float(row_now.get("close", float("nan"))),
                })
        except Exception as e:
            if DEBUG_SIGNALS:
                logger.debug("Signal-Auswertung bei i={} übersprungen: {}", i, e)
            continue

    return longs, shorts