# WORKFLOW STATUS — TradingBot (Crypto)

## Aktive Phase
**Phase 0 — Ordnung, Controller-Core & Bau-Automatisierung (Safety-first)**

## Modus / Safety-Gates
- Default-Modus: **DRY_RUN / Paper / Testnet**
- Live-Trading (Mainnet): **GESPERRT**, bis Safety-Gates erfüllt und explizit freigeschaltet
- Secrets: **niemals** im Repo/Chat/Logs; nur `.env` lokal + `.env.example` ohne echte Werte

## Was läuft gerade?
- Prozess/Service: _—_
- Modus: _DRY_RUN / Testnet / Mock_
- Host/Port (falls relevant): _—_

## Letzter bekannter Stand
- Entry-Point(s): _z.B. bot/run.py, scripts/..._
- Exchange/SDK: _z.B. Bybit REST/WebSocket_
- Datenquellen: _—_
- Order-Ausführung: _disabled / dry-run / enabled (nur wenn freigeschaltet)_

## Letzter erfolgreicher Verify
- Befehl:
  - `...`
- Ergebnis (kurz):
  - `OK / FAIL`
- Datum:
  - `YYYY-MM-DD`

## Aktuelles Problem / Blocker
- _—_

## Nächster Schritt (genau 1 Punkt)
- _Repo-Snapshot (Projekt-Root + Strukturbaum) erstellen_

## Änderungslog (kurz)
- `YYYY-MM-DD` — 00_GOV angelegt (Status, Patch Rules, Decision Log)

## Artefakte / Outputs
- Logs: `logs/` (nicht versionieren)
- Runs: `runs/` (nicht versionieren)
- Reports: `reports/` (nach Bedarf, ohne Secrets)
