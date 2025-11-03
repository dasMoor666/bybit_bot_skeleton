# Bybit Testnet Bot — Skeleton (EMA Crossover + Volume/ATR Filters)

**Modus:** DRY_RUN standardmässig aktiv. Passt zu: „aggressiv, aber risiko-bewusst“.

## Schnellstart
1. Python 3.11 nutzen
2. `pip install -r requirements.txt`
3. `.env.example` zu `.env` kopieren und Werte prüfen
4. `python -m bot.run` (DRY_RUN=true) — liest lokale CSVs in `data/` falls vorhanden, ansonsten nur Framework-Checks.
5. Später: `DRY_RUN=false` setzen und in `bot/broker.py` die echten Bybit-Calls (pybit) aktivieren.

## Struktur
```
bot/
  config.py       # Settings via Pydantic
  indicators.py   # EMA, RSI, ATR%, Volumen-SMA
  strategy.py     # Einstiegssignale (LONG/SHORT)
  risk.py         # Exits (Gegensignal + Failsafes), Limits
  broker.py       # Order-Layer (DRY_RUN-Simulation & Platzhalter für pybit)
  data.py         # Backfill (CSV/REST), Livefeed (WS) — Stubs enthalten
  utils.py        # Spread-Guard, Session, Zeit, Logging-Helfer
  run.py          # Main-Loop: init -> backfill -> live loop (WS Stub)
logs/             # runtime.log, orders.csv, trades.csv, equity_curve.csv
reports/          # Daily-Reports (JSON)
data/             # Optionale CSV-Kerzen (Symbol_5m.csv)
```

## Hinweise
- **Backtesting/Live-Parität**: Alle Guards (ATR/Spread/Session/Cooldown) sind auch im Backtest zu beachten.
- **Positions-Modus**: One-Way, isolated, 3x leverage (Default).
- **Exits**: Gegensignal + Hard SL/TP + Trailing + Timeout.
- **A/B-Tests**: Volumen-Multiplikator 1.5 Standard, 1.3 aggressiv.

## TODO (für echte Orders)
- In `broker.py` die Abschnitte mit `# TODO: REAL ORDER` aktivieren und `pybit`-Client anlegen (Testnet-Endpunkte).
- In `data.py` WebSocket-Subscribe für 5m-Klines (Testnet) implementieren.
- TODO: Signal-Logik feinschleifen
- TODO: Signal-Logik feinschleifen
