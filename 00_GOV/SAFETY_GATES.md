# SAFETY GATES — TradingBot (Crypto)

Diese Datei beschreibt die verbindlichen Safety-Gates.
Wichtig: In Phase 0 bleibt **Order-Ausführung gesperrt** (NO-TRADE). Alles ist read-only oder dry_run.

## Gate-Status (Phase 0 / 0B / 0C)
- ✅ Public Testnet Read-only: erlaubt
- ✅ Private Testnet Read-only (mit lokalen .env Keys): erlaubt
- ✅ dry_run (Intent-Simulation): erlaubt
- ❌ place_order / execute / live trading: GESPERRT (GateClosed)

## Verboten in Phase 0 (immer)
- Orders platzieren / ändern / canceln (egal ob Testnet oder Mainnet)
- Withdraw / Transfer / Subaccount Transfers
- Secrets ausgeben (Keys, Signatures, komplette Responses mit sensitiven Feldern)

## Minimal erlaubte Read-only Endpoints
Public (ohne Auth):
- Market time / tickers
- Kline / candles

Private (Auth notwendig, aber read-only):
- Wallet balance (read-only)
- Positions (read-only)

## Verify-Checkliste (muss grün sein)
### Public Testnet
- `python bot/controller_cli.py get_state --symbol BTCUSDT --category linear`
- `python bot/controller_cli.py get_candles --symbol BTCUSDT --category linear --interval 15 --limit 5`
- `python bot/controller_cli.py analyze --symbol BTCUSDT --category linear --interval 15 --limit 200`
Erwartung: HTTP 200, JSON Output, kein Crash.

### Private Testnet (nur lokal mit .env)
- `set -a; source .env; set +a; python bot/controller_cli.py get_private_state --category linear --symbol BTCUSDT`
Erwartung: `retCode=0` bei wallet und positions.

### Safety-Gate Proof (NO-TRADE)
- `python bot/controller_cli.py place_order --symbol BTCUSDT --side Buy --qty 0.001`
Erwartung: Blockiert mit `GateClosed`, kein Crash.

## Wie wird Live-Trading später freigeschaltet?
Nicht in Phase 0.
Freischaltung erst in einer späteren Phase inkl.:
- schriftlicher Gate-Plan + Review
- separate “Unlock”-Mechanik (lokal, nicht versioniert)
- Limits (max size / max orders / kill-switch)
- Tests + Monitoring + Audit-Logs
