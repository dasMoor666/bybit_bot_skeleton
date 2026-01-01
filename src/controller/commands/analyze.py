from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Any, Dict, List

from src.controller.analysis import compute_indicators, simple_signal
from src.controller.cli import (
    ControllerResult,
    _utc_iso,
    _load_settings_summary,
    _public_base_url,
    _http_get_json,
    _parse_kline_list,
    _print_json,
)

def run(args: argparse.Namespace) -> int:
    settings = _load_settings_summary()
    base_url = _public_base_url(settings)

    symbol = (args.symbol or "BTCUSDT").strip().upper()
    category = (args.category or "linear").strip()
    interval = str(args.interval or "15").strip()
    limit = int(args.limit or 200)
    limit = max(1, min(limit, 1000))

    url = f"{base_url}/v5/market/kline?category={category}&symbol={symbol}&interval={interval}&limit={limit}"
    raw = _http_get_json(url)
    candles: List[Dict[str, Any]] = _parse_kline_list(raw)

    ind = compute_indicators(candles)
    sig = simple_signal(ind)

    data: Dict[str, Any] = {
        "mode": "read_only",
        "note": "Read-only analysis on public candles. No auth. No orders.",
        "settings": settings,
        "query": {"category": category, "symbol": symbol, "interval": interval, "limit": limit},
        "candles_count": len(candles),
        "indicators": {"sma20": ind.sma20, "sma50": ind.sma50, "rsi14": ind.rsi14},
        "signal": sig,
        "public": {"base_url": base_url, "kline": raw},
    }

    res = ControllerResult(ok=True, command="analyze", ts=_utc_iso(), data=data)
    _print_json(asdict(res))
    return 0
