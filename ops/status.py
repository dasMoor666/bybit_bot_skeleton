# --- Pfad-Fix (immer ganz oben) ---
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- Imports ---
from bot.config import SETTINGS
from pybit.unified_trading import HTTP
import pprint

# --- PrettyPrinter für saubere Ausgabe ---
pp = pprint.PrettyPrinter(indent=2, width=100)

# --- API Session ---
s = HTTP(timeout=60,  testnet=SETTINGS.bybit_testnet,
    api_key=SETTINGS.bybit_api_key,
    api_secret=SETTINGS.bybit_api_secret
)

# --- Standardsymbol, falls in config kein Symbol gesetzt ist ---
symbol = getattr(SETTINGS, "symbol", "BTCUSDT") or "BTCUSDT"

# --- Positionen, offene Orders und Fills anzeigen ---
print("=== Positions ===")
pp.pprint(s.get_positions(category="linear", symbol=symbol))

print("\n=== Open orders ===")
pp.pprint(s.get_open_orders(category="linear", symbol=symbol))

print("\n=== Recent fills ===")
pp.pprint(s.get_executions(category="linear", symbol=symbol))