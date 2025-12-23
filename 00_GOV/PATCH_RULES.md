# PATCH RULES — TradingBot (Crypto)
Verbindliche Arbeitsregeln für maximale Kontrolle, Auditierbarkeit und Sicherheit.

## 0) Absolute Prioritäten
1. **Controller-Primat:** Controller zuerst. Strategie/Edge/Optimierung ist Phase >0.
2. **Phase-Primat:** Genau eine aktive Phase. Alles muss eindeutig dazu gehören.
3. **Keine stillen Änderungen:** Keine Dateiänderungen ohne explizite Freigabe.
4. **Auditierbarkeit:** Jede Ausführung/Änderung muss nachvollziehbar sein (Outputs/Logs).
5. **Safety-Primat:** Default **DRY_RUN/Testnet/Mock**. Live ist gesperrt bis freigegeben.

## 1) Rollen
- **ChatGPT:** analysiert, plant, formuliert Befehle (keine Pseudo-Ausführung).
- **Controller/Repo:** führt aus, liefert stdout/stderr/exit_code/Artefakte.

## 2) PATCH OK – Pflicht
ChatGPT darf Dateien nur ändern, wenn der User exakt schreibt: **PATCH OK**

### 2.1 Patch-Ankündigungspflicht (vor PATCH OK)
Vor jeder Änderung muss ChatGPT einen **PATCH-PLAN** posten:
- Ziel (1 Satz)
- Exakte Dateiliste (Pfade)
- Exakte Wirkung (was ändert sich)
- Risiko (kurz)
- Verify-Schritt (genauer Terminal-Befehl)

### 2.2 PATCH OK ist nur gültig, wenn dabei ist
- Ziel-Datei(en) als Pfade
- Kontext-Snapshot inkl. `ls -la <ziel-datei>` für jede betroffene Datei

## 3) Patch-/Kontext-Gate (Snapshot)
Vor jedem Patch MUSS vorliegen (aus Projekt-Root):
- `pwd`
- `git status -sb` (falls Git)
- `ls -la | head`
- `ls -la <ziel-datei>` für jede Datei

## 4) Ausführungsprotokoll
Jede Anweisung muss markiert sein:
- **[DATEI]** = in Datei/IDE ändern
- **[TERMINAL]** = Befehl ausführen

Pro Schritt nur **eine** Aktion:
- Patch **oder** Test
- Wenn mehrere: nummeriert 1/2/3 und einzeln abarbeiten.

## 5) Verify-Regel (nach JEDEM Patch)
Minimal, reproduzierbar:
- Python: `python -m py_compile <file>` oder `python -m py_compile $(git ls-files '*.py')`
- Zusätzlich: 1 Controller-Healthcheck (sofern vorhanden)

## 6) Secrets (bindend)
- Keine Keys/Tokens/Cookies in Chat/Repo/Logs.
- `.env` lokal, nicht versioniert.
- `.env.example` ohne echte Werte.
- Wenn Keys irgendwo auftauchen: **sofort rotieren**.

## 7) Trading-Sicherheits-Gates (Phase 0)
- Default: `DRY_RUN=true`
- Mainnet/Live nur bei expliziter Freischaltung (z.B. `EXECUTE=true` + Gate-Check)
- Hard-Limits (später): max order size, max daily loss, kill-switch
- Bei Fehlern: “No-trade”-Mode statt “best effort”

## 8) BLOK-PRINZIP
Wenn neue Datei/Abschnitt: ChatGPT liefert **vollständige Blöcke**.
Keine “ändere Zeile X” ohne ausdrücklichen Wunsch.
