#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-Runner für Bybit-Strategie
- Misst Marktlage via ATR% (Volatilität) + Volumen-Ratio
- Wählt automatisch Preset: conservative / balanced / aggressive
- Startet scripts/run_strategy.py mit passenden ENV-Parametern

Konfigurierbare Schwellwerte:
- ATR_THRESHOLDS: (low, high) in Prozent
- VOL_RATIO_THRESHOLDS: (low, high) als Multiplikator ggü. Durchschnitt

Aufrufbeispiel:
  SYM=BTCUSDT TF=15 DRY=1 EXECUTE=0 PYTHONPATH=. .venv/bin/python scripts/auto_run.py
"""
import os, json, subprocess, time
from typing import List, Dict, Any
from pybit.unified_trading import HTTP
from bot.config import SETTINGS as S

# -------- Schwellenwerte / Defaults --------
ATR_LOOKBACK      = int(os.environ.get("ATR_LOOKBACK", "14"))
VOL_LOOKBACK      = int(os.environ.get("VOL_LOOKBACK", "20"))
ATR_THRESHOLDS    = (
    float(os.environ.get("ATR_PCT_LOW", "0.30")),  # unter 0.30% = conservative
    float(os.environ.get("ATR_PCT_HIGH","0.80")),  # über 0.80% = aggressive (sonst balanced)
)
VOL_RATIO_THRESHOLDS = (
    float(os.environ.get("VOL_RATIO_LOW",  "0.70")),  # < 0.7x = schwach
    float(os.environ.get("VOL_RATIO_HIGH", "1.30")),  # > 1.3x = stark
)

# Symbole/TF/Modi (können per ENV überschrieben werden)
SYM = os.environ.get("SYM", "BTCUSDT")
TF  = os.environ.get("TF",  "15")           # Bybit-Intervals als String: "1","3","5","15","60",...
DRY = os.environ.get("DRY", "1")            # 1 = Dry-Run
EXECUTE = os.environ.get("EXECUTE", "0")    # 1 = Orders platzieren

# Grundverhalten
ALLOW_SHORT = os.environ.get("ALLOW_SHORT", "1")  # Shorts erlauben
USE_PREV_CLOSE_DEF = os.environ.get("USE_PREV_CLOSE", "0")  # Referenz Close der vorigen Kerze

# Pfade
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON = os.path.join(ROOT, ".venv", "bin", "python")
RUN_SCRIPT = os.path.join(ROOT, "scripts", "run_strategy.py")

# ---------- Hilfsfunktionen ----------
def http():
    return HTTP(timeout=60,  api_key=S.bybit_api_key, api_secret=S.bybit_api_secret, testnet=S.bybit_testnet)

def fetch_klines(client) -> List[Dict[str, Any]]:
    r = client.get_kline(category="linear", symbol=SYM, interval=TF, limit=max(VOL_LOOKBACK+2, ATR_LOOKBACK+2, 100))
    L = (r["result"] or {}).get("list") or []
    out = []
    # Bybit list-Format: [ start, open, high, low, close, volume, turnover, ... ]
    for row in L:
        out.append({
            "ts":    int(row[0])//1000,
            "open":  float(row[1]),
            "high":  float(row[2]),
            "low":   float(row[3]),
            "close": float(row[4]),
            "volume":float(row[5]),
        })
    return out

def atr(kl: List[Dict[str, Any]], n: int) -> float:
    trs = []
    # TR über die letzten n abgeschlossenen Kerzen (hinter der laufenden)
    for i in range(1, min(len(kl), n+1)):
        h = float(kl[-i]["high"])
        l = float(kl[-i]["low"])
        pc = float(kl[-i-1]["close"])
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    return sum(trs)/len(trs) if trs else 0.0

def avg_volume(kl: List[Dict[str, Any]], n: int) -> float:
    if len(kl) < n+1: 
        return 0.0
    # Durchschnitt über die letzten n abgeschlossenen Kerzen
    vols = [float(k["volume"]) for k in kl[-n-1:-1]]
    return sum(vols)/len(vols) if vols else 0.0

def decide_preset(atr_pct: float, vol_ratio: float) -> str:
    low, high = ATR_THRESHOLDS
    vlow, vhigh = VOL_RATIO_THRESHOLDS
    # sehr niedrige Vola → conservative
    if atr_pct < low:
        return "conservative"
    # sehr hohe Vola + starkes Volumen → aggressive
    if atr_pct > high and vol_ratio > vhigh:
        return "aggressive"
    # sonst balanced
    return "balanced"

def preset_params(name: str) -> Dict[str, str]:
    """
    Liefert ENV-Parameter für das Preset.
    Werte bewusst konservativ gewählt – bitte nach Geschmack feinjustieren.
    """
    if name == "conservative":
        return {
            "LOOKBACK":      "20",
            "VOL_MULT":      "1.20",   # Vol-Filter strenger
            "EPS_BREAK":     "0.003",  # 0.3% Toleranz
            "ATR_SL":        "1.00",
            "ATR_TP":        "1.20",
            "USE_PREV_CLOSE":"1",      # stabilere Breakout-Referenz
        }
    if name == "aggressive":
        return {
            "LOOKBACK":      "10",
            "VOL_MULT":      "0.70",   # Vol-Filter lockerer
            "EPS_BREAK":     "0.010",  # 1.0% Toleranz
            "ATR_SL":        "1.50",
            "ATR_TP":        "2.40",
            "USE_PREV_CLOSE":"0",
        }
    # balanced (default)
    return {
        "LOOKBACK":      "15",
        "VOL_MULT":      "1.00",
        "EPS_BREAK":     "0.005",      # 0.5%
        "ATR_SL":        "1.20",
        "ATR_TP":        "1.80",
        "USE_PREV_CLOSE":"0",
    }

def run_strategy(env: Dict[str, str]) -> int:
    cmd = [PYTHON, RUN_SCRIPT]
    # Freundliche Konsolenzeile
    print(json.dumps({
        "auto_run": True,
        "sym": env.get("SYM"),
        "tf": env.get("TF"),
        "dry_run": env.get("DRY"),
        "execute": env.get("EXECUTE"),
        "preset": env.get("__PRESET__"),
        "params": {
            "LOOKBACK": env.get("LOOKBACK"),
            "VOL_MULT": env.get("VOL_MULT"),
            "EPS_BREAK": env.get("EPS_BREAK"),
            "ATR_SL": env.get("ATR_SL"),
            "ATR_TP": env.get("ATR_TP"),
            "ALLOW_SHORT": env.get("ALLOW_SHORT"),
            "USE_PREV_CLOSE": env.get("USE_PREV_CLOSE"),
        }
    }, ensure_ascii=False))
    p = subprocess.run(cmd, env=env, text=True)
    return p.returncode

# ---------- main ----------
def main():
    client = http()
    kl = fetch_klines(client)
    if len(kl) < max(ATR_LOOKBACK+2, VOL_LOOKBACK+2):
        print(json.dumps({"error":"not_enough_bars","have":len(kl)}, ensure_ascii=False))
        raise SystemExit(1)

    last_closed = kl[-2]  # abgeschlossene Kerze als Referenz
    px = float(last_closed["close"])
    a = atr(kl, ATR_LOOKBACK)
    atr_pct = (a / px * 100.0) if px > 0 else 0.0

    avgv = avg_volume(kl, VOL_LOOKBACK)
    vol_last = float(last_closed["volume"])
    vol_ratio = (vol_last / avgv) if avgv > 0 else 1.0

    preset = decide_preset(atr_pct, vol_ratio)
    params = preset_params(preset)

    # ENV zusammenbauen
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": ROOT,
        "SYM": SYM,
        "TF": TF,
        "DRY": DRY,
        "EXECUTE": EXECUTE,
        "ALLOW_SHORT": ALLOW_SHORT,
        "__PRESET__": preset,
        # übernommene Params:
        **params
    })

    # Infozeile
    print(json.dumps({
        "market_metrics": {
            "price": px,
            "atr": a,
            "atr_pct": round(atr_pct, 3),
            "vol_last": vol_last,
            "vol_avg": avgv,
            "vol_ratio": round(vol_ratio, 2),
        },
        "decision": preset
    }, ensure_ascii=False))

    # Strategie ausführen
    rc = run_strategy(env)
    raise SystemExit(rc)

if __name__ == "__main__":
    main()
