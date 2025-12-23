# WORKFLOW STATUS — TradingBot (Crypto)

## Aktive Phase
**Phase 0B — Controller-Core minimal (deterministisch, auditierbar, NO-TRADE)**

## Modus / Safety-Gates
- Default-Modus: **DRY_RUN / Paper / Testnet**
- Live-Trading (Mainnet): **GESPERRT**, bis Safety-Gates erfüllt und explizit freigeschaltet
- Secrets: **niemals** im Repo/Chat/Logs; nur `.env` lokal + `.env.example` ohne echte Werte
- Cursor/Agent: **Manual/Review only**, kein Auto-Apply

## Was läuft gerade?
- Prozess/Service: _—_
- Modus: _NO-TRADE (Controller CLI)_
- Host/Port (falls relevant): _—_

## Letzter erfolgreicher Verify
- Befehl:
  - `python -m py_compile bot/controller_cli.py`
  - `python bot/controller_cli.py healthcheck`
- Ergebnis (kurz):
  - Controller CLI läuft, gibt JSON aus, keine Secrets
- Datum:
  - 2025-12-23

## Stand (kurz)
- Phase 0A abgeschlossen: `00_GOV/` + Repo-Hygiene
- Phase 0B gestartet:
  - `02_CONTROLLER/README.md`

## Nächster Schritt
- Controller-Wiring (read-only): `get_state` erweitert um echte Exchange-State-Abfrage (nur GET, kein Order-Posting)
- Dependency-Baseline: requirements/lock + reproduzierbarer venv-Setup

## Blocker / Risiken
- Abhängigkeiten in venv können “driften” → wir brauchen reproduzierbare Install-Schritte
- Live-Trading bleibt gesperrt, bis Safety-Gates schriftlich erfüllt sind
