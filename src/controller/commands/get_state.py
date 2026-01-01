from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Any, Dict

from src.controller.cli import (
    ControllerResult,
    _utc_iso,
    _load_settings_summary,
    _public_base_url,
    _http_get_json,
    _print_json,
)

def run(args: argparse.Namespace) -> int:
    settings = _load_settings_summary()
    base_url = _public_base_url(settings)

    symbol = (args.symbol or "BTCUSDT").strip().upper()
    category = (args.category or "linear").strip()

    market_time = _http_get_json(f"{base_url}/v5/market/time")
    ticker = _http_get_json(f"{base_url}/v5/market/tickers?category={category}&symbol={symbol}")

    data: Dict[str, Any] = {
        "mode": "read_only",
        "note": "Public read-only Bybit GETs only. No auth. No orders.",
        "settings": settings,
        "public": {
            "base_url": base_url,
            "market_time": market_time,
            "ticker": ticker,
        },
        "query": {"category": category, "symbol": symbol},
    }

    res = ControllerResult(ok=True, command="get_state", ts=_utc_iso(), data=data)
    _print_json(asdict(res))
    return 0
