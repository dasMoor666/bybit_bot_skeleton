# -*- coding: utf-8 -*-
"""
Schlanke Logging- und Notifier-Utilities ohne Zirkularimporte.
Verwendet JSON-Lines-Logs in ~/Desktop/bybit_bot_skeleton/logs

API:
- log_event(kind: str, payload: dict) -> dict
- notify(message: str, title: str = "Bybit Bot") -> None
"""

import os, json, datetime as dt, subprocess, shlex

# Basisverzeichnis = Repo-Root relativ zu dieser Datei
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR  = os.path.join(BASE_DIR, "logs")

# Dateinamen je nach Event-Art
EVENTS_LOG = os.path.join(LOG_DIR, "events.log")
HEALTH_LOG = os.path.join(LOG_DIR, "health.log")
ALERTS_LOG = os.path.join(LOG_DIR, "alerts.log")

def _ensure_dirs():
    os.makedirs(LOG_DIR, exist_ok=True)

def _now_rec(kind: str, payload: dict) -> dict:
    return {
        "ts":  int(dt.datetime.utcnow().timestamp()),
        "iso": dt.datetime.utcnow().isoformat() + "Z",
        "kind": kind,
        "data": payload or {}
    }

def _target_log_for(kind: str) -> str:
    # Health-Events in health.log, alles andere in events.log
    if kind.startswith("health"):
        return HEALTH_LOG
    return EVENTS_LOG

def log_event(kind: str, payload: dict) -> dict:
    """
    Schreibt einen JSON-Datensatz in das passende Log
    und gibt ihn als dict zurück.
    """
    _ensure_dirs()
    rec = _now_rec(kind, payload)
    path = _target_log_for(kind)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec

def _macos_notify(title: str, message: str) -> bool:
    """
    Versucht eine native macOS Notification via osascript.
    Gibt True bei Erfolg, sonst False.
    """
    try:
        # sauberes Escaping
        osa = (
            'display notification {msg} with title {title}'
            .format(
                msg=shlex.quote(str(message)),
                title=shlex.quote(str(title))
            )
        )
        subprocess.run(
            ["osascript", "-e", osa],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False

def notify(message: str, title: str = "Bybit Bot") -> None:
    """
    Versucht zuerst eine macOS-Notification, fällt sonst auf Console zurück.
    Loggt zusätzlich in alerts.log.
    """
    _ensure_dirs()
    # Alerts-Log mitschreiben
    line = {
        "ts":  int(dt.datetime.utcnow().timestamp()),
        "iso": dt.datetime.utcnow().isoformat() + "Z",
        "alert": str(message),
        "title": str(title)
    }
    with open(ALERTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")

    if _macos_notify(title, message):
        return

    # Fallback: Console
    print(f"[NOTIFY] {title}: {message}")
