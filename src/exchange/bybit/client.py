# bot/exchange_utils.py
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional, Tuple
import time

from pybit.unified_trading import HTTP
from bot.config import SETTINGS


def get_client() -> HTTP:
    """Erzeuge einen Bybit-HTTP Client basierend auf SETTINGS."""
    return HTTP(timeout=60,  testnet=SETTINGS.bybit_testnet,
        api_key=SETTINGS.bybit_api_key,
        api_secret=SETTINGS.bybit_api_secret,
    )


def round_tick(x: Decimal, tick: Decimal) -> Decimal:
    """Rundet x auf die Bybit-Tickgröße nach unten."""
    return (int((x / tick).to_integral_value(rounding=ROUND_DOWN)) * tick)


def _get_symbol() -> str:
    sym = getattr(SETTINGS, "symbol", "BTCUSDT")
    return sym or "BTCUSDT"


def _fetch_pos(s: HTTP, sym: str) -> Dict[str, Any]:
    return s.get_positions(category="linear", symbol=sym)["result"]["list"][0]


def force_flat_now(
    s: Optional[HTTP] = None,
    sym: Optional[str] = None,
    poll_seconds: float = 4.0,
    use_mark_for_stop: bool = True,
) -> Dict[str, Any]:
    """
    Versucht eine offene Position sofort flat zu stellen.
    1) Market-Gegenorder (reduceOnly)
    2) Falls nach kurzem Poll nicht flat: Stop-Market knapp hinterm Preis (korrekte triggerDirection)
    Gibt Status + letzte Position + offene Orders zurück.
    """
    s = s or get_client()
    sym = sym or _get_symbol()

    # 0) Position holen
    pos = _fetch_pos(s, sym)
    qty_str: str = pos["size"]
    side: str = pos["side"]
    if not qty_str or Decimal(qty_str) == 0:
        return {
            "status": "already_flat",
            "pos": pos,
            "opens": s.get_open_orders(category="linear", symbol=sym),
            "meta": {"symbol": sym},
        }

    # 1) Market reduceOnly in Gegenrichtung
    opp_side = "Buy" if side == "Sell" else "Sell"
    market_res = s.place_order(
        category="linear",
        symbol=sym,
        side=opp_side,
        orderType="Market",
        qty=str(qty_str),
        reduceOnly=True,
        positionIdx=pos.get("positionIdx", 0),
        timeInForce="IOC",
    )

    # 2) Kurz pollen, ob flat
    t_end = time.time() + max(0.0, poll_seconds)
    last_pos = pos
    while time.time() < t_end:
        time.sleep(0.5)
        last_pos = _fetch_pos(s, sym)
        if Decimal(last_pos["size"]) == 0:
            return {
                "status": "closed_market",
                "pos": last_pos,
                "opens": s.get_open_orders(category="linear", symbol=sym),
                "meta": {"symbol": sym, "market_res": market_res},
            }

    # 3) Fallback: Stop-Market knapp hinter Preis
    #    Richtige Richtung: SHORT schließen → Preis steigt → triggerDirection=1
    #                        LONG  schließen → Preis fällt → triggerDirection=2
    ticker = s.get_tickers(category="linear", symbol=sym)["result"]["list"][0]
    last = Decimal(ticker["lastPrice"])
    instr = s.get_instruments_info(category="linear", symbol=sym)["result"]["list"][0]
    tick = Decimal(instr["priceFilter"]["tickSize"])

    if last_pos["side"] == "Sell":  # SHORT → Buy Stop etwas über last
        trigger = max(round_tick(last * Decimal("1.0001"), tick), (last // tick) * tick + tick)
        close_side = "Buy"
        trigger_dir = 1
    else:  # LONG → Sell Stop etwas unter last
        trigger = min(round_tick(last * Decimal("0.9999"), tick), (last // tick) * tick - tick)
        close_side = "Sell"
        trigger_dir = 2

    stop_res = s.place_order(
        category="linear",
        symbol=sym,
        side=close_side,
        orderType="Market",
        qty=str(last_pos["size"]),
        reduceOnly=True,
        closeOnTrigger=True,
        positionIdx=last_pos.get("positionIdx", 0),
        stopOrderType="StopLoss",
        triggerBy=("MarkPrice" if use_mark_for_stop else "LastPrice"),
        triggerPrice=str(trigger),
        triggerDirection=trigger_dir,
        timeInForce="IOC",  # neutral; bei Market-Stop ignoriert
    )

    # 4) Noch einmal kurz schauen, ob dadurch bereits flat
    time.sleep(1.5)
    final_pos = _fetch_pos(s, sym)
    status = "closed_stop" if Decimal(final_pos["size"]) == 0 else "armed_stop"

    return {
        "status": status,
        "pos": final_pos,
        "opens": s.get_open_orders(category="linear", symbol=sym),
        "meta": {
            "symbol": sym,
            "market_res": market_res,
            "stop_res": stop_res,
            "trigger": str(trigger),
            "trigger_dir": trigger_dir,
            "used_triggerBy": "MarkPrice" if use_mark_for_stop else "LastPrice",
        },
    }
