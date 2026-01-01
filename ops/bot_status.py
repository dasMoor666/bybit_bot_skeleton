from decimal import Decimal, InvalidOperation
import json
from pybit.unified_trading import HTTP
from bot.config import SETTINGS

s = HTTP(timeout=60,  testnet=SETTINGS.bybit_testnet,
         api_key=SETTINGS.bybit_api_key,
         api_secret=SETTINGS.bybit_api_secret)

sym = getattr(SETTINGS, "symbol", "BTCUSDT") or "BTCUSDT"

def D(x):
    try:
        return Decimal(str(x))
    except (InvalidOperation, TypeError):
        return None

# --- Position ---
p_res = s.get_positions(category="linear", symbol=sym)["result"]
plist = p_res.get("list", []) or []
pos   = plist[0] if plist else {"size":"0", "side":"", "markPrice":""}

size = pos.get("size","0")
side = pos.get("side","")
unrp = pos.get("unrealisedPnl","")
pos_mark = pos.get("markPrice","")

# --- Ticker ---
t = s.get_tickers(category="linear", symbol=sym)["result"]["list"][0]
last  = t.get("lastPrice","")
bid1  = t.get("bid1Price","")
ask1  = t.get("ask1Price","")
tick_mark  = t.get("markPrice","")
index = t.get("indexPrice","")

# --- Preiswahl mit Sanity-Check ---
lastD  = D(last)
markD1 = D(tick_mark)
markD2 = D(pos_mark)
indexD = D(index)

# Basis-Regeln:
# 1) Bevorzuge Mark-Price, wenn plausibel
# 2) Wenn Mark/Last stark von Index abweichen (Faktor > 3), nimm Index
# 3) Falls alles Mist ist, gib leeren Safe-Preis und setze Hinweis
note = []
safe = None

candidates = [p for p in [markD1, markD2, lastD] if p is not None]

if indexD is not None:
    # prüfe starke Abweichung
    bad = []
    for tag, val in [("last", lastD), ("mark1", markD1), ("mark2", markD2)]:
        if val is not None and val > 0:
            ratio = (val / indexD) if val >= indexD else (indexD / val)
            if ratio > 3:
                bad.append(tag)
    if bad:
        note.append(f"glitch_vs_index:{','.join(bad)}")
        safe = indexD

if safe is None:
    # nimm erste plausible Quelle in Reihenfolge mark, mark(pos), last
    for val in candidates:
        if val is not None and val > 0:
            safe = val
            break

if safe is None and indexD is not None:
    safe = indexD

status = "flat" if (size in ("0","0.0") or D(size) == 0) else "open"

out = {
  "symbol": sym,
  "status": status,
  "pos_size": size,
  "pos_side": side,
  "unrealised_pnl": unrp,
  "last_price": last,
  "bid1": bid1,
  "ask1": ask1,
  "mark_price_from_ticker": tick_mark,
  "mark_price_from_pos": pos_mark,
  "index_price": index,
  "safe_price": (str(safe) if safe is not None else ""),
  "notes": ";".join(note) if note else ""
}

print(json.dumps(out, ensure_ascii=False))
