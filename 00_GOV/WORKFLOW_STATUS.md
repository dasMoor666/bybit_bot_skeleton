# WORKFLOW STATUS — TradingBot (Crypto)

## Aktive Phase
**Phase 0C — Controller-Core (deterministisch, auditierbar, NO-TRADE, Testnet Public+Private Read-only OK)**

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
  - `python bot/controller_cli.py get_state --symbol BTCUSDT --category linear`
  -t/controller_cli.py get_candles --symbol BTCUSDT --category linear --interval 15 --limit 5`
  - `python bot/controller_cli.py analyze --symbol BTCUSDT --category linear --interval 15 --limit 200`
  - `set -a; source .env; set +a; python bot/controller_cli.py get_private_state --category linear --symbol BTCUSDT`
  - `python bot/controller_cli.py place_order --symbol BTCUSDT --side Buy --qty 0.001`  # MUSS blocken (GateClosed)
- Ergebnis (kurz):
  - Bybit **Testnet** erreichbar (HTTP 200), Public Read-only State/Candles/Analyse liefern JSON
  - Private Read-only (Wallet/Positions) liefert `retCode=0`
  - `place_order` ist **geblockt** (NO-TRADE), crasht nicht
- Datum:
  - 2025-12-25

## Stand (kurz)
- Phase 0A abgeschlossen:
  - `00_GOV/` Baseline + Repo-Hygiene
- Phase 0B abgeschlossen (stabil):
  - `bot/controller_cli.py`: `healthcheck`, `get_state`, `get_candles`, `analyze`, `dry_run`
  - SSL robust (certifi), Output deterministisch (JSON)
  - `requirements.lock` vorhanden (reproduzierbarer Env-Stand)
- Phase 0C abgeschlossen (Read-only + Gates):
  - `get_private_state` (private read-only) funktioniert im Testnet mit lokalen `.env` Keys
  - `place_order` existiert nur als **blocked** Command (GateClosed)

## Nächster Schritt (genau 1 Punkt)
- **Safety-Gates finalisieren & dokumentieren** (00_GOV/SAFETY_GATES.md + “Wie schalte ich Live frei?” Checkliste, weiterhin NO-TRADE default)

## Blocker / Risiken
- Import-Side-Effects in Legacy-Modulen möglich (z.B. Logs beim Import) → später entkoppeln
- Abhängigkeiten können “driften” → `requirements.lock` muss die Quelle bleiben
- Live-Trading bleibt gesperrt, bis Safety-Gates schriftlich erfüllt sind

## Verify — Testnet Connectivity (Public + Private, read-only)
- Public:
  - `python bot/controller_cli.py get_state --symbol BTCUSDT --category linear`
- Private (requires .env locally):
  - `set -a; source .env; set +a; python bot/controller_cli.py get_private_state --category linear --symbol BTCUSDT`
- Erwartung:
  - `retCode=0` bei wallet + posSafety Gate (NO-TRADE)
- `python bot/controller_cli.py place_order --symbol BTCUSDT --side Buy --qty 0.001`
- Erwartung:
  - `"error": "GateClosed: ..."` und kein Crash
