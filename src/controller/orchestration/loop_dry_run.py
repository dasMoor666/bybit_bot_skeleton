#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

from src.controller.analysis import compute_indicators, simple_signal

def utc_ts() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def sh(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or f"command failed: {cmd}")
    return json.loads(p.stdout)

def main():
    symbol = "BTCUSDT"
    category = "linear"
    interval = "15"
    limit = "200"

    out = sh(["python","-m","src.controller","get_candles",
              "--symbol", symbol, "--category", category,
              "--interval", interval, "--limit", limit])

    candles = out["data"]["candles"]
    ind = compute_indicators(candles)
    sig = simple_signal(ind)

    run = {
        "ts": utc_ts(),
        "symbol": symbol,
        "category": category,
        "interval": interval,
        "candles_count": len(candles),
        "indicators": {"sma20": ind.sma20, "sma50": ind.sma50, "rsi14": ind.rsi14},
        "signal": sig,
        "note": "NO-TRADE dry-run loop (no orders)",
    }

    Path("runs").mkdir(exist_ok=True)
    fn = Path("runs") / f"dry_run_{int(time.time())}.json"
    fn.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "saved": str(fn), "run": run}, ensure_ascii=False))

if __name__ == "__main__":
    main()
