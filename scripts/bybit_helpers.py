from pybit.unified_trading import HTTP
from bot.config import SETTINGS as S
import time, math, json

def tick_digits(x: str) -> int:
    s = str(x)
    return len(s.split(".")[1]) if (x is not None and "." in s) else 0

def safe_digits(tick_str, price):
    d = tick_digits(str(tick_str))
    if d == 0:
        if price < 1:   return 6
        if price < 10:  return 3
        if price < 100: return 2
        return 2
    return d

def round_up_step(x: float, step: float) -> float:
    return math.ceil(x / step) * step

def place_market_with_tp_sl(symbol: str, side: str, tp_bps=30, sl_bps=20, min_notional=5.0):
    """
    Plaziert Market-Order und setzt danach TP/SL (in Basis-Punkten).
    tp_bps=30  -> +0.30%, sl_bps=20 -> -0.20% (bei Buy).
    """
    s = HTTP(timeout=60,  api_key=S.bybit_api_key, api_secret=S.bybit_api_secret, testnet=S.bybit_testnet)

    # --- Instrument & Orderbuch ---
    info = s.get_instruments_info(category="linear", symbol=symbol)
    item = ((info or {}).get("result") or {}).get("list", [{}])[0]
    tick_str = (item.get("priceFilter") or {}).get("tickSize") or "0.0001"
    lsf = (item.get("lotSizeFilter") or {})
    qty_step = float(lsf.get("qtyStep") or "1")
    min_qty  = float(lsf.get("minOrderQty") or "1")
    min_not  = float(lsf.get("minNotionalValue") or min_notional)

    ob = s.get_orderbook(category="linear", symbol=symbol, limit=1)
    ask = float((((ob or {}).get("result") or {}).get("a") or [[None,0]])[0][0] or 0.0)
    bid = float((((ob or {}).get("result") or {}).get("b") or [[None,0]])[0][0] or 0.0)
    px  = ask if side=="Buy" else bid
    if px <= 0:
        return [{"stage":"price_fetch_failed","ask":ask,"bid":bid}]

    # --- Menge so wählen, dass Notional passt ---
    qty_need = max(min_qty, (min_not*1.02)/px)  # +2% Puffer
    qty = round_up_step(qty_need, qty_step)

    # --- Order ---
    order = s.place_order(category="linear", symbol=symbol, side=side, orderType="Market", qty=str(qty), reduceOnly=False)
    out = [{"stage":"order_placed","retCode":order.get("retCode"),"retMsg":order.get("retMsg"),
            "qty":qty,"px":px,"notional":round(px*qty,6)}]
    if order.get("retCode") != 0:
        return out

    # --- Position pollen bis gefüllt ---
    avg = 0.0; size = 0.0; trade_mode = None
    for i in range(12):
        time.sleep(0.5)
        pos = s.get_positions(category="linear", symbol=symbol)
        lst = ((pos or {}).get("result") or {}).get("list") or []
        p   = lst[0] if lst else {}
        avg = float(p.get("avgPrice") or 0.0)
        try: size = float(p.get("size") or 0.0)
        except: size = 0.0
        trade_mode = p.get("tradeMode")
        out.append({"stage":"poll_position","try":i+1,"avgPrice":avg,"size":size,"tradeMode":trade_mode})
        if size>0 and avg>0: break

    if not (size>0 and avg>0):
        out.append({"stage":"abort_set_stops","reason":"no_filled_position","avgPrice":avg,"size":size})
        return out

    # --- Digits & Format ---
    digits = safe_digits(tick_str, avg)
    def fmt(v: float) -> str: return f"{v:.{digits}f}"
    tp_val = avg * (1 + tp_bps/10000.0) if side=="Buy" else avg * (1 - tp_bps/10000.0)
    sl_val = avg * (1 - sl_bps/10000.0) if side=="Buy" else avg * (1 + sl_bps/10000.0)
    tp_str, sl_str = fmt(tp_val), fmt(sl_val)
    if tp_str in ("0","0.0") or sl_str in ("0","0.0"):
        digits = max(digits, 4)
        tp_str, sl_str = fmt(tp_val), fmt(sl_val)

    out.append({"stage":"format_debug","tick_str":tick_str,"digits":digits,"avg":avg,
                "tp_val":tp_val,"sl_val":sl_val,"tp_str":tp_str,"sl_str":sl_str})

    # --- positionIdx je nach Modus ---
    position_idx = 0 if trade_mode != 3 else (1 if side=="Buy" else 2)

    # --- Stops setzen ---
    stops = s.set_trading_stop(category="linear", symbol=symbol, positionIdx=position_idx,
                               takeProfit=tp_str, stopLoss=sl_str,
                               tpTriggerBy="LastPrice", slTriggerBy="LastPrice")
    out.append({"stage":"stops_set","positionIdx":position_idx,"retCode":stops.get("retCode"),"retMsg":stops.get("retMsg")})
    return out

def dry_preview(symbol="DOGEUSDT", side="Buy"):
    """Nur Infos ausgeben, keine Order."""
    s = HTTP(api_key=S.bybit_api_key, api_secret=S.bybit_api_secret, testnet=S.bybit_testnet)
    info = s.get_instruments_info(category="linear", symbol=symbol)
    item = ((info or {}).get("result") or {}).get("list", [{}])[0]
    tick_str = (item.get("priceFilter") or {}).get("tickSize")
    lsf = (item.get("lotSizeFilter") or {})
    ob = s.get_orderbook(category="linear", symbol=symbol, limit=1)
    ask = float((((ob or {}).get("result") or {}).get("a") or [[None,0]])[0][0] or 0.0)
    d = safe_digits(tick_str, ask or 1.0)
    print(json.dumps({
        "symbol":symbol, "side":side,
        "tick_str":tick_str, "qtyStep": lsf.get("qtyStep"), "minQty": lsf.get("minOrderQty"),
        "minNotional": lsf.get("minNotionalValue"),
        "ask": ask, "digits": d
    }, indent=2))
