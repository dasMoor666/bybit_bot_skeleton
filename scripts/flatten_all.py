#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flatten helper: schliesst alle offenen Positionen im Testnet.
"""
import time
from pybit.unified_trading import HTTP
from bot.config import SETTINGS as S

SYMS = ["BTCUSDT"]   # Erweiterbar, falls du z. B. ETHUSDT testest
s = HTTP(timeout=60,  api_key=S.bybit_api_key, api_secret=S.bybit_api_secret, testnet=S.bybit_testnet)

def pos_side_sz(p):
    return float(p.get("size","0") or 0), p.get("side")  # side: Buy / Sell

for sym in SYMS:
    r = s.get_positions(category="linear", symbol=sym)
    lst = (r.get("result") or {}).get("list") or []
    for p in lst:
        sz, side = pos_side_sz(p)
        if sz <= 0: 
            continue
        closing_side = "Sell" if side == "Buy" else "Buy"
        print(f"[FLATTEN] {sym}: close {sz} ({side}) via {closing_side} reduceOnly")
        s.place_order(category="linear", symbol=sym, side=closing_side,
                      orderType="Market", qty=str(sz), reduceOnly=True, timeInForce="IOC")
        time.sleep(0.5)

print("[FLATTEN] done.")
