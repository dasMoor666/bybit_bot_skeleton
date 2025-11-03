#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time, json, subprocess, sys, os
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

def run_panic():
    proj = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    exe = os.path.join(proj, "scripts", "panic_close.py")
    return subprocess.run([sys.executable, exe], capture_output=True, text=True).stdout

def main():
    s = http()
    p = get_pos(s); oo = get_orders(s)
    print(json.dumps({"ts": int(time.time()), "pos_open": bool(p), "open_orders": len(oo)}))
    if p or len(oo) > 0:
        out = run_panic()
        if out:
            print(out.strip())
    else:
        print(json.dumps({"result": "FLAT"}))
    # Ende: one-shot

if __name__ == "__main__":
    main()
