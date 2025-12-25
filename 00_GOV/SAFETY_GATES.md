# SAFETY GATES — TradingBot (Crypto)

Status: **NO-TRADE / Read-only**
- In Phase 0 sind **keine** Order-Commands erlaubt.
- `place_order` ist absichtlich implementiert, aber **immer blockiert** (GateClosed).

## Grundregeln (bindend)
- Keys/Secrets: nur lokal `.env`, niemals committen/teilen.
- Testnet ist erlaubt. Mainnet bleibt gesperrt, bis Gates schriftlich erfüllt sind.
- Alle kritischen Aktionen müssen auditierbar sein (Commands + Output).

## Gate: Order-Ausführung
**GATE_CLOSED = TRUE**

Freischaltung (später, Phase >0) nur wenn ALLE Punkte erfüllt sind:
- [ ] Explizite Freigabe im Projekt (schriftlich)
- [ ] Risk-Limits + Max Drawdown + Positionsizing definiert
- [ ] Kill-Switch / Panic-Close getestet
- [ ] Dry-run/Simulation über längere Strecke ohne Fehlverhalten
- [ ] Logging ohne Secrets verifiziert
- [ ] Separate “EXECUTE=1” Freigabe-Mechanik + Review

Bis dahin gilt:
- `=> **immer GateClosed**
- Nutze `dry_run` für Intent-Simulation
