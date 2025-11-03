import os, json, sys, datetime as dt
from pybit.unified_trading import HTTP
from bot.config import SETTINGS as S

# ---- STRATEGY AUSWAHL (per ENV STRAT) ----
_STRAT = (os.environ.get("STRAT") or "mom_s").lower()
if _STRAT in ("mom_s","momscalp","mom-s"):
    from strategies.mom_s import MomScalp as StrategyClass
else:
    from strategies.mom_s import MomScalp as StrategyClass

# ---- BYBIT HELFER ----
from scripts.bybit_helpers import place_market_with_tp_sl

LOGF = "logs/alerts.log"

def log(line: str):
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}Z] {line}"
    try:
        with open(LOGF,"a",encoding="utf-8") as f:
            f.write(msg+"\n")
    except Exception:
        pass
    print(msg)

def main():
    SYM = os.environ.get("SYM","DOGEUSDT")
    TF  = os.environ.get("TF","1")
    N   = int(os.environ.get("LOOKBACK","2"))
    USE_PREV = int(os.environ.get("USE_PREV_CLOSE","1"))==1
    ALLOW_SHORT = int(os.environ.get("ALLOW_SHORT","1"))==1
    DEBUG = int(os.environ.get("DEBUG","1"))==1
    EPS = float(os.environ.get("EPS_BREAK","0"))

    DRY = int(os.environ.get("DRY","1"))==1
    EXECUTE = int(os.environ.get("EXECUTE","0"))==1

    TP_BPS = int(os.environ.get("TP_BPS","30"))   # 30 = +0.30%
    SL_BPS = int(os.environ.get("SL_BPS","20"))   # 20 = -0.20%

    s = HTTP(timeout=60,  api_key=S.bybit_api_key, api_secret=S.bybit_api_secret, testnet=S.bybit_testnet)

    # --- Klines holen (älteste->neueste) ---
    r = s.get_kline(category="linear", symbol=SYM, interval=TF, limit=N+3)
    lst = ((r or {}).get("result") or {}).get("list") or []
    if len(lst) < N+2:
        log(f"NO_DATA {SYM} bars={len(lst)} need>={N+2}")
        return 0
    kl = [{"open":x[1], "high":x[2], "low":x[3], "close":x[4], "volume":x[5]} for x in lst]  # Reihenfolge belassen

    # --- Strategy instanzieren ---
    strat = StrategyClass(lookback=N, eps_break=EPS, allow_short=ALLOW_SHORT, debug=DEBUG, use_prev_close=USE_PREV)

    state={}
    sig = strat.generate(kl, state)

    if not sig:
        dbg = state.get("__debug__", {})
        log(f"No signal | dbg={json.dumps(dbg)}")
        return 0

    # --- Signal vorhanden ---
    log(f"SIGNAL ⚡ {SYM} {sig.side} px={sig.price} tp={sig.tp} sl={sig.sl} note={getattr(sig,'note','')}")
    if DRY and not EXECUTE:
        log("DRY=1 → keine Order platziert.")
        return 0

    if EXECUTE:
        # echte Order + TP/SL
        side = "Buy" if sig.side.lower().startswith("b") else "Sell"
        out = place_market_with_tp_sl(SYM, side, tp_bps=TP_BPS, sl_bps=SL_BPS, min_notional=5.0)
        log("EXEC_RESULT " + json.dumps(out))
        return 0

    return 0

if __name__ == "__main__":
    sys.exit(main())
