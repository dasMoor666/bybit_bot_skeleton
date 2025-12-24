# WORKFLOW STATUS — TradingBot (Crypto)

## Aktive Phase
**Phase 0B — Controller-Core (deterministisch, auditierbar, NO-TRADE, Read-only Testnet OK)**

## Modus / Safety-Gates
- Default-Modus: **NO-TRADE / DRY_RUN / Testnet**
- Live-Trading (Mainnet): **GESPERRT**, bis Safety-Gates erfüllt und explizit freigeschaltet
- Secrets: **niemals** im Repo/Chat/Logs; nur `.env` lokal + `.env.example` ohne echte Werte
- Cursor/Agent: **Manual/Review only**, kein Auto-Apply

## Was läuft gerade?
- Prozess/Service: _—_
- Modus: _NO-TRADE (Controller CLI)_
- Host/Port (falls relevant): _—_

## Letzter erfolgreicher Verify
- Befehle:
  - `python -m py_compile bot/controller_cli.py`
  - `python bot/controller_cli.py get_state --symbol BTCUSDT --category l`python bot/controller_cli.py get_candles --symbol BTCUSDT --category linear --interval 15 --limit 5`
  - `python bot/controller_cli.py analyze --symbol BTCUSDT --category linear --interval 15 --limit 200`
- Ergebnis (kurz):
  - Bybit **Testnet** erreichbar (HTTP 200), Read-only State/Candles/Analyse liefern JSON, keine Secrets
- Datum:
  - 2025-12-24

## Stand (kurz)
- Phase 0A abgeschlossen:
  - `00_GOV/` Baseline + Repo-Hygiene
- Phase 0B abgeschlossen (stabil):
  - `bot/controller_cli.py`:
    - `healthcheck`, `get_state`, `get_candles`, `analyze`, `dry_run`
    - SSL robust (certifi), Output deterministisch (JSON)
  - `requirements.lock` vorhanden (reproduzierbarer Env-Stand)

## Nächster Schritt (genau 1 Punkt)
- **Phase 0C starten:** Private **read-only** Testnet-Checks (Balance/Positions), weiterhin **NO-TRADE**, keine Secrets im Output

## Blocker / Risiken
- Import-Side-Effects in Legacy-Modulen möglich (z.B. Logs beim Import) → später entkoppeln
- Live-Trading bleibt gesperrt, bis Safety-Gathriftlich erfüllt sind
