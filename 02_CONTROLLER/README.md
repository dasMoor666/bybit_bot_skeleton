# 02_CONTROLLER — Minimal Controller Core (Phase 0B)

Ziel: deterministischer, auditierbarer Einstiegspunkt (CLI), der nur:
- healthcheck (Runtime/Imports/Config)
- get_state (read-only)
- dry_run (Simulation, keine Orders)

Wichtig:
- Default ist NO-TRADE (keine Live-Ausführung).
- Secrets werden nie ausgegeben (nur vorhanden: ja/nein).

Commands:

1) Healthcheck
   python bot/controller_cli.py healthcheck

2) State (read-only)
   python bot/controller_cli.py get_state

3) Dry run (Simulation)
   python bot/controller_cli.py dry_run --symbol BTCUSDT --side buy --qty 0.001
