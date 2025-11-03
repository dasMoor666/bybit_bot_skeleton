from __future__ import annotations
from pybit.unified_trading import HTTP
import os
import time
import sys
import json
import traceback

def place_order_and_stops(s: HTTP, sig: dict) -> dict:
    """
    Robuster Live-Exec:
      1) Entry als MARKET (sicherer als IOC-Limit)
      2) Auf Fill/Position warten
      3) TP/SL = Distanz vom Signalpreis, um avgPrice gelegt
      4) Tick-Rundung + Richtungssanity (Buy: TP>avg, SL<avg; Sell: TP<avg, SL>avg)
    Erwartet sig = {side, size, price, sl, tp}.
    One-Way-Modus: positionIdx=0.
    """
    SYM = os.environ.get("SYM","BTCUSDT")
    side = sig["side"]            # "Buy" / "Sell"
    qty  = str(sig["size"])
    sig_px = float(sig["price"])
    sig_sl = float(sig["sl"])
    sig_tp = float(sig["tp"])

    info = _instr_info(s, SYM)
    tick = float(((info.get("priceFilter") or {}).get("tickSize")) or 0.1)

    # --- Entry: Market ---
    order = s.place_order(
        category="linear", symbol=SYM, side=side,
        orderType="Market", qty=qty, reduceOnly=False, timeInForce="IOC"
    )

    # --- Warten bis Position existiert ---
    pos = None
    for _ in range(40):
        time.sleep(0.25)
        pos = _position(s, SYM)
        if pos["size"] > 0 and pos["side"] == side:
            break
    if not pos or pos["size"] <= 0 or pos["side"] != side:
        raise RuntimeError("Entry nicht gefüllt – keine passende Position gefunden.")

    avg = float(pos["avgPrice"] or sig_px or 0)

    # --- Distanz vom Signal übernehmen, um avg legen ---
    if side == "Buy":
        dist_tp = max(sig_tp - sig_px, tick)
        dist_sl = max(sig_px - sig_sl, tick)
        tp_val  = avg + dist_tp
        sl_val  = max(0.0, avg - dist_sl)
        # Sanity Richtung:
        if tp_val <= avg: tp_val = avg + max(tick, abs(dist_tp))
        if sl_val >= avg: sl_val = max(0.0, avg - max(tick, abs(dist_sl)))
    else:  # Sell
        dist_tp = max(sig_px - sig_tp, tick)
        dist_sl = max(sig_sl - sig_px, tick)
        tp_val  = max(0.0, avg - dist_tp)
        sl_val  = avg + dist_sl
        # Sanity Richtung:
        if tp_val >= avg: tp_val = max(0.0, avg - max(tick, abs(dist_tp)))
        if sl_val <= avg: sl_val = avg + max(tick, abs(dist_sl))

    # --- Tick-Rundung ---
    tp_str = _tick_round(tp_val, tick)
    sl_str = _tick_round(sl_val, tick)

    # --- Stops setzen (One-Way) ---
    stops = s.set_trading_stop(
        category="linear", symbol=SYM, positionIdx=0,
        takeProfit=tp_str, stopLoss=sl_str,
        tpTriggerBy="LastPrice", slTriggerBy="LastPrice"
    )

    # Debug-Ausgabe, hilft bei künftigen Issues
    try:
        print(json.dumps({
            "exec": {"avg": avg, "tick": tick, "tp": tp_val, "sl": sl_val,
                     "tp_str": tp_str, "sl_str": sl_str, "side": side}
        }))
    except Exception:
        pass

    return {"order": order, "stops": stops, "avgPrice": avg,
            "tick": tick, "dist_tp": dist_tp, "dist_sl": dist_sl}

def _tick_round(x: float, tick: float) -> str:
    if tick <= 0: 
        return f"{x:.1f}"
    # runden auf Tick
    q = round(x / tick) * tick
    # Bybit mag Strings; zu viele Nachkommastellen vermeiden
    return f"{q:.{max(0, str(tick)[::-1].find('.'))}f}".rstrip('0').rstrip('.') if '.' in f"{q}" else str(q)

def _instr_info(s: HTTP, symbol: str) -> dict:
    r = s.get_instruments_info(category="linear", symbol=symbol)
    return ((r or {}).get("result") or {}).get("list",[{}])[0]

def _best_price(s: HTTP, symbol: str, side: str) -> float:
    ob = s.get_orderbook(category="linear", symbol=symbol, limit=1)
    arr = ((ob or {}).get("result") or {}).get("b",[]) if side=="Sell" else ((ob or {}).get("result") or {}).get("a",[])
    if arr and len(arr[0])>=1:
        return float(arr[0][0])
    # Fallback: letzte Ticker-Price
    tk = s.get_tickers(category="linear", symbol=symbol)
    px = (((tk or {}).get("result") or {}).get("list") or [{}])[0].get("lastPrice")
    return float(px or 0)

def _position(s: HTTP, symbol: str) -> dict:
    r = s.get_positions(category="linear", symbol=symbol)
    lst = ((r or {}).get("result") or {}).get("list") or []
    # Bybit listet getrennt Buy/Sell; nimm die mit size>0
    for p in lst:
        try:
            if float(p.get("size") or 0) > 0:
                return {
                    "size": float(p.get("size") or 0),
                    "side": p.get("side"),
                    "avgPrice": float(p.get("avgPrice") or 0),
                    "positionIdx": int(p.get("positionIdx") or 0),
                }
        except Exception:
            pass


    return {"size": 0.0, "side": None, "avgPrice": 0.0, "positionIdx": 0}
# ==== STRAT_ENV_BEGIN ====
import os as _os
_STRAT = (_os.environ.get("STRAT") or "mom_s").lower()
try:
    if _STRAT in ("mom_s","momscalp","mom-s"):
        from strategies.mom_s import MomScalp as StrategyClass
    else:
        # Fallback: MomScalp, wenn Unbekanntes kommt
        from strategies.mom_s import MomScalp as StrategyClass
except Exception as _e:
    # harter Fallback, damit der Runner nicht crasht
    from strategies.mom_s import MomScalp as StrategyClass
# ==== STRAT_ENV_END ====
