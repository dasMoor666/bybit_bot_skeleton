import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bot.config import SETTINGS
from pybit.unified_trading import HTTP

s = HTTP(timeout=60,  testnet=SETTINGS.bybit_testnet,
    api_key=SETTINGS.bybit_api_key,
    api_secret=SETTINGS.bybit_api_secret
)

symbol = getattr(SETTINGS, "symbol", "BTCUSDT") or "BTCUSDT"

pos = s.get_positions(category="linear", symbol=symbol)["result"]["list"][0]
qty, side = pos["size"], pos["side"]

if qty and side == "Sell":
    print("Close SHORT:", qty)
    print(s.place_order(category="linear", symbol=symbol, side="Buy", orderType="Market", qty=qty, reduceOnly=True))
elif qty and side == "Buy":
    print("Close LONG:", qty)
    print(s.place_order(category="linear", symbol=symbol, side="Sell", orderType="Market", qty=qty, reduceOnly=True))
else:
    print("Keine offene Position gefunden.")