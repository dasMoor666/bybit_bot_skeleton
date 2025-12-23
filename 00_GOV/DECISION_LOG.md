# DECISION LOG — TradingBot (Crypto)

> Zweck: Nach Pausen sofort verstehen, **warum** etwas so gebaut wurde.

## Format
- Datum:
- Entscheidung:
- Kontext:
- Optionen (kurz):
- Begründung:
- Konsequenzen / Follow-ups:
- Verify:

---

## 2025-12-23
- Entscheidung: 00_GOV eingeführt (Status / Patch Rules / Decision Log)
- Kontext: Projekt wird neu ausgerichtet, zuerst Ordnung & kontrollierter Controller-Core
- Optionen:
  1) Direkt Strategie/Trading weiterbauen
  2) Erst Governance + Safety + Controller-Core
- Begründung: Auditierbarkeit + Risiko-Reduktion, reproduzierbarer Betrieb
- Konsequenzen / Follow-ups:
  - Repo-Snapshot erstellen
  - Secrets aus Repo entfernen, `.env.example` einführen
  - Controller-Commands definieren: healthcheck/get_state/dry_run
- Verify:
  - `ls -la 00_GOV`
