# scripts/utils_close.py
# -----------------------------------------------------
# Notfall-Schließfunktion für Bybit-Testnet / Live
# Schließt offene Positionen unabhängig vom Status.
# -----------------------------------------------------

from pybit.unified_trading import HTTP
from bot.config import SETTINGS as S


def force_close_open_position(symbol="BTCUSDT"):
    """
    Erzwingt das Schließen einer offenen Position, falls vorhanden.
    Prüft zuerst, ob eine Position offen ist, und schließt sie dann
    mit einer Market-Order (reduceOnly=False, um Testnet-Glitches zu umgehen).
    """
    s = HTTP(timeout=60,  api_key=S.bybit_api_key,
        api_secret=S.bybit_api_secret,
        testnet=S.bybit_testnet,
    )

    print(f"🔍 Suche offene Position für {symbol} …")
    L = (s.get_positions(category="linear", symbol=symbol)["result"]["list"] or [])
    P = next((p for p in L if float(p.get("size") or 0) > 0), None)

    if not P:
        print("✅ Keine offene Position gefunden.")
        return

    side = P["side"]
    size = P["size"]
    opp = "Sell" if side == "Buy" else "Buy"

    print(f"⚡ Force-Closing {side} {size} {symbol} …")
    r = s.place_order(
        category="linear",
        symbol=symbol,
        side=opp,
        orderType="Market",
        qty=size,
        reduceOnly=False,
    )

    print("🧾 API-Antwort:", r)
    print("📊 Positionen nachher:")
    print(s.get_positions(category="linear", symbol=symbol))
