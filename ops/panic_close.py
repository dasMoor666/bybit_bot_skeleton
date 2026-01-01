#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time, sys, json
from decimal import Decimal
from pybit.unified_trading import HTTP
from bot.config import SETTINGS as S

SYM = "BTCUSDT"

def http():
    return HTTP(timeout=60,  api_key=S.bybit_api_key, api_secret=S.bybit_api_secret, testnet=S.bybit_testnet)

def get_pos(s):
    L = (s.get_positions(category="linear", symbol=SYM)["result"]["list"] or [])
    return next((p for p in L if float(p.get("size") or 0) > 0), None)

def get_orders(s):
    res = s.get_open_orders(category="linear", symbol=SYM)["result"]
    return (res or {}).get("list", []) or []

def cancel_all(s):
    try:
        return s.cancel_all_orders(category="linear", symbol=SYM)
    except Exception as e:
        return {"error": str(e)}

def try_reduce_only(s, side, size):
    opp = "Sell" if side == "Buy" else "Buy"
    return s.place_order(category="linear", symbol=SYM, side=opp, orderType="Market", qty=size, reduceOnly=True)

def try_force_market(s, side, size):
    opp = "Sell" if side == "Buy" else "Buy"
    return s.place_order(category="linear", symbol=SYM, side=opp, orderType="Market", qty=size, reduceOnly=False)

def try_ioc_crossed(s, side, size):
    tk = s.get_tickers(category="linear", symbol=SYM)["result"]["list"][0]
    bid = Decimal(tk["bid1Price"]); ask = Decimal(tk["ask1Price"])
    opp = "Sell" if side == "Buy" else "Buy"
    px = (ask * Decimal("1.40") if opp == "Buy" else bid * Decimal("0.60"))
    px = str(px.quantize(Decimal("0.1")))
    return s.place_order(category="linear", symbol=SYM, side=opp,
                         orderType="Limit", qty=size, price=px,
                         timeInForce="IOC", reduceOnly=False)

def main():
    s = http()
    cancel_all(s)  # Vorab alles löschen

    for round_ in range(1, 6):
        p = get_pos(s)
        if not p:
            oo = get_orders(s)
            print(json.dumps({"status":"flat","round":round_,"open_orders":len(oo)}))
            sys.exit(0)

        side, size = p["side"], p["size"]
        actions = []

        # 1) reduceOnly Market
        try: actions.append({"reduceOnlyMarket": try_reduce_only(s, side, size)})
        except Exception as e: actions.append({"reduceOnlyMarket_err": str(e)})
        time.sleep(0.8)
        if not get_pos(s):
            cancel_all(s); print(json.dumps({"status":"flat","round":round_,"actions":actions})); sys.exit(0)

        # 2) force Market
        try: actions.append({"forceMarket": try_force_market(s, side, size)})
        except Exception as e: actions.append({"forceMarket_err": str(e)})
        time.sleep(0.8)
        if not get_pos(s):
            cancel_all(s); print(json.dumps({"status":"flat","round":round_,"actions":actions})); sys.exit(0)

        # 3) IOC crossed
        try: actions.append({"iocCrossed": try_ioc_crossed(s, side, size)})
        except Exception as e: actions.append({"iocCrossed_err": str(e)})
        time.sleep(0.8)
        cancel_all(s)
        print(json.dumps({"status":"retry","round":round_,"actions":actions}))

    print(json.dumps({"status":"not_flat_after_retries","pos":get_pos(s),"open_orders":len(get_orders(http()))}))
    sys.exit(2)

if __name__ == "__main__":
    main()
