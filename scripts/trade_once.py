#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/trade_once.py
Erstellt eine einmalige Buy/Sell-Order auf Bybit (Testnet)
mit robuster Fehlerbehandlung gegen Glitches (ErrCode 110003).
"""

import os, sys, json, time, pprint
from decimal import Decimal, ROUND_DOWN, getcontext
from pybit.unified_trading import HTTP

# --- ensure project root on sys.path ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# ---------------------------------------

from bot.config import SETTINGS

pp = pprint.PrettyPrinter(indent=2, width=100)
D = Decimal
getcontext().prec = 28


# ============================================================
# Hilfsfunktionen
# ============================================================

def round_tick(x: Decimal, tick: Decimal) -> Decimal:
    return (x / tick).to_integral_value(rounding=ROUND_DOWN) * tick if tick > 0 else x


def load_filters(s, sym):
    """Liest Preis- und Mengenfilter von Bybit."""
    info = s.get_instruments_info(category="linear", symbol=sym)["result"]["list"][0]
    tick = D(info["priceFilter"]["tickSize"])
    qty_step = D(info["lotSizeFilter"]["qtyStep"])
    min_qty = D(info["lotSizeFilter"]["minOrderQty"])
    min_price = D(info["priceFilter"]["minPrice"])
    max_price = D(info["priceFilter"]["maxPrice"])
    return tick, qty_step, min_qty, min_price, max_price


def safe_place_ioc(s, sym, side, px, qty, tick, min_price, max_price, tries=6):
    """Versucht IOC mehrfach, bei 110003 automatisch Preis anpassen."""
    print(f"[Filters] tick={tick} min_price={min_price} max_price={max_price}")
    for i in range(tries):
        p = round_tick(px + D("0.1") * i, tick)
        print(f"Try #{i+1}: IOC {side} @ {p}")
        try:
            res = s.place_order(
                category="linear",
                symbol=sym,
                side=side,
                orderType="Limit",
                price=str(p),
                qty=str(qty),
                timeInForce="IOC",
                reduceOnly=False,
            )
            return res
        except Exception as e:
            msg = str(e)
            if "110003" in msg:
                print(f"⚠️  110003 @ {p} → nudge price …")
                continue
            else:
                print(f"❌  Fehler: {msg}")
                time.sleep(0.3)
    # Fallback: mehrere weiter entfernte Limits
    for j in range(6):
        mult = D("1.1") + D("0.1") * j if side == "Buy" else D("0.9") - D("0.1") * j
        widened = round_tick(px * mult, tick)
        print(f"[Widen {j+1}] IOC {side} @ {widened}")
        try:
            res = s.place_order(
                category="linear",
                symbol=sym,
                side=side,
                orderType="Limit",
                price=str(widened),
                qty=str(qty),
                timeInForce="IOC",
                reduceOnly=False,
            )
            return res
        except Exception as e:
            print("Fehler:", e)
    return {"retCode": -1, "retMsg": "keine Order erfolgreich"}


# ============================================================
# Hauptfunktion
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--side", required=True, choices=["Buy", "Sell"])
    parser.add_argument("--notional", required=True, type=float)
    parser.add_argument("--base", type=float, help="Basispreis zur Simulation")
    parser.add_argument("--force-cross", action="store_true", help="setzt Limit ans andere OB-Ende")
    args = parser.parse_args()

    sym = getattr(SETTINGS, "symbol", "BTCUSDT")

    s = HTTP(timeout=60,  testnet=getattr(SETTINGS, "bybit_testnet", True),
        api_key=SETTINGS.bybit_api_key,
        api_secret=SETTINGS.bybit_api_secret
    )

    # Pre-Check
    pos = s.get_positions(category="linear", symbol=sym)["result"]["list"][0]
    pre = {
        "pos_size": pos["size"],
        "pos_side": pos["side"],
        "open_orders": len(s.get_open_orders(category="linear", symbol=sym)["result"]["list"])
    }
    print(json.dumps({"pre": pre}))

    # Preise
    t = s.get_tickers(category="linear", symbol=sym)["result"]["list"][0]
    bid1 = D(t["bid1Price"])
    ask1 = D(t["ask1Price"])
    index = D(t["indexPrice"])
    safe = index
    basis = D(str(args.base)) if args.base else safe

    tick, qty_step, min_qty, min_price, max_price = load_filters(s, sym)
    qty = max(min_qty, D(str(args.notional)) / basis)
    qty = (qty / qty_step).to_integral_value(rounding=ROUND_DOWN) * qty_step

    # Limitpreis wählen
    limit_px = basis * (D("1.02") if args.side == "Buy" else D("0.98"))
    if args.force_cross:
        limit_px = ask1 if args.side == "Buy" else bid1

    plan = {
        "side": args.side,
        "limit_price": str(limit_px),
        "qty": str(qty),
        "notional_usdt": str(args.notional),
        "safe_price": str(safe),
        "bid1": str(bid1),
        "ask1": str(ask1),
        "index": str(index),
        "notes": ("base_override" if args.base else "live") + ("+force_cross" if args.force_cross else ""),
        "force_cross": args.force_cross,
    }
    print(json.dumps({"symbol": sym, "plan": plan}))

    print("\nORDER (IOC-Limit):")
    res1 = safe_place_ioc(s, sym, args.side, limit_px, qty, tick, min_price, max_price)
    pp.pprint(res1)

    # Nachstatus
    post = {
        "fills": s.get_executions(category="linear", symbol=sym),
        "positions": s.get_positions(category="linear", symbol=sym),
    }
    print("\nPOST:")
    pp.pprint(post)


if __name__ == "__main__":
    main()
