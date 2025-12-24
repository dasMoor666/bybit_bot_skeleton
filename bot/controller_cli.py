#!/usr/bin/env python3
"""
Minimal Controller CLI (Phase 0B)
- healthcheck: runtime/import/config check
- get_state: READ-ONLY public Bybit GETs (no auth, no orders)
- get_candles: READ-ONLY public Bybit Kline (no auth, no orders)
- analyze: READ-ONLY technical analysis on public candles (SMA/RSI), no trading
- dry_run: validate + log an order intent (no execution)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _print_json(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_asciiFalse) + "\n")


def _safe_bool_env(name: str) -> Optional[bool]:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return None


@dataclass
class ControllerResult:
    ok: bool
    command: str
    ts: str
    data: Dict[str, Any]
    error: Optional[str] = None


def _load_settings_summary() -> Dict[str, Any]:
    """
    Tries to load bot.config.Settings if available.
    Never returns secrets, only presence flags and harmless metadata.
    """
    summary: Dict[str, Any] = {
        "config_loaded": False,
        "settings_class": None,
        "env_flags": {
            "DRY_RUN": _safe_bool_env("DRY_RUN"),
            "EXECUTE": _safe_bool_env("EXECUTE"),
            "TESTNET": _safe_bool_env("TESTNET"),
        },
        "secrets_present": {
            "BYBIT_API_KEY": bool(os.getenv("BYBIT_API_KEY")),
            "BYBIT_API_SECRET": bool(os.getenv("BYBIT_API_SECRET")),
            "API_KEY": bool(os.getenv("API_KEY")),
            "API_SECRET": bool(os.getenv("API_SECRET")),
        },
    }

    try:
        from bot.config import Settings  # type: ignore
        s = Settings()
        summary["config_loaded"] = True
        summary["settings_class"] = "bot.config.Settings"

        # only harmless fields if they exist
        for field in [
            "mode", "env", "exchange", "base_url", "testnet",
            "bybit_testnet", "bybit_base_url"
        ]:
            if hasattr(s, field):
                val = getattr(s, field)
                summary[field] = val if isinstance(val, (str, int, float, bool)) or val is None else str(val)

    except Exception as e:
        summary["config_error"] = f"{type(e).__name__}: {e}"

    return summary


def _public_base_url(settings: Dict[str, Any]) -> str:
    # Decide public base URL (no auth)
    testnet_flag = None
    for key in ("bybit_testnet", "testnet"):
        if isinstance(settings.get(key), bool):
            testnet_flag = settings.get(key)
            break
    if testnet_flag is None:
        testnet_flag = settings.get("env_flags", {}).get("TESTNET") is True

    return "https://api-testnet.bybit.com" if testnet_flag else "https://api.bybit.com"


def _http_get_json(url: str, timeout_s: int = 10) -> Dict[str, Any]:
    """Public GET helper. No auth. No secrets. SSL uses certifi if available."""
    try:
        import urllib.request
        import ssl

        # Robust SSL: prefer certifi CA bundle, fallback to system default
        try:
            import certifi  # type: ignore
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "TradingBot-Controller/0B (read-only)",
                "Accept": "application/json",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout_s, context=ctx) as resp:
            status = getattr(resp, "status", 200)
            raw = resp.read().decode("utf-8", errors="replace")

        try:
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {"_raw": raw}

        return {"ok": True, "status": status, "data": data, "url": url}

    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "url": url}


def cmd_healthcheck(_: argparse.Namespace) -> int:
    data: Dict[str, Any] = {
        "python": sys.version.split()[0],
        "cwd": os.getcwd(),
        "settings": _load_settings_summary(),
        "imports": {},
    }

    # Import probes (may have side effects in legacy modules; still useful)
    for mod in ["bot", "bot.config", "bot.run"]:
        try:
            __import__(mod)
            data["imports"][mod] = True
        except Exception as e:
            data["imports"][mod] = f"{type(e).__name__}: {e}"

    res = ControllerResult(ok=True, command="healthcheck", ts=_utc_iso(), data=data)
    _print_json(asdict(res))
    return 0


def cmd_get_state(args: argparse.Namespace) -> int:
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


def _parse_kline_list(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Bybit v5 market/kline returns list items like:
    [ startTime, open, high, low, close, volume, turnover ]
    """
    out: List[Dict[str, Any]] = []
    data = (raw or {}).get("data") if isinstance(raw, dict) else None
    if not isinstance(data, dict):
        return out
    result = data.get("result") or {}
    lst = result.get("list") or []
    if not isinstance(lst, list):
        return out

    for item in lst:
        if not isinstance(item, list) or len(item) < 7:
            continue
        try:
            ts_ms = int(item[0])
            o = float(item[1]); h = float(item[2]); l = float(item[3]); c = float(item[4])
            v = float(item[5]); t = float(item[6])
        except Exception:
            continue
        out.append({
            "ts_ms": ts_ms,
            "open": o, "high": h, "low": l, "close": c,
            "volume": v, "turnover": t,
        })
    # API commonly returns newest-first; sort oldest->newest for analysis
    out.sort(key=lambda x: x["ts_ms"])
    return out


def cmd_get_candles(args: argparse.Namespace) -> int:
    settings = _load_settings_summary()
    base_url = _public_base_url(settings)

    symbol = (args.symbol or "BTCUSDT").strip().upper()
    category = (args.category or "linear").strip()
    interval = str(args.interval or "15").strip()
    limit = int(args.limit or 200)
    if limit < 1:
        limit = 1
    if limit > 1000:
        limit = 1000  # bybit limit guard

    url = f"{base_url}/v5/market/kline?category={category}&symbol={symbol}&interval={interval}&limit={limit}"
    raw = _http_get_json(url)
    candles = _parse_kline_list(raw)

    data: Dict[str, Any] = {
        "mode": "read_only",
        "note": "Public read-only candles (kline). No auth. No orders.",
        "settings": settings,
        "public": {
            "base_url": base_url,
            "kline": raw,
        },
        "query": {"category": category, "symbol": symbol, "interval": interval, "limit": limit},
        "candles_count": len(candles),
        "candles": candles,
    }

    res = ControllerResult(ok=True, command="get_candles", ts=_utc_iso(), data=data)
    _print_json(asdict(res))
    return 0


def _compute_sma(values: "list[float]", period: int) -> Optional[float]:
    if period <= 0 or len(values) < period:
        return None
    window = values[-period:]
    return float(sum(window) / period)


def _compute_rsi_wilder(closes: "list[float]", period: int = 14) -> Optional[float]:
    if period <= 0 or len(closes) < period + 1:
        return None
    # Wilder RSI using pandas if available for stability
    try:
        import pandas as pd  # type: ignore

        s = pd.Series(closes, dtype="float64")
        delta = s.diff()
        gain = delta.clip(lower=0.0)
        loss = (-delta).clip(lower=0.0)

        # Wilder smoothing
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace({0.0: float("nan")})
        rsi = 100.0 - (100.0 / (1.0 + rs))
        last = float(rsi.iloc[-1])
        if last != last:  # NaN check
            return None
        return last
    except Exception:
        return None


def cmd_analyze(args: argparse.Namespace) -> int:
    settings = _load_settings_summary()
    base_url = _public_base_url(settings)

    symbol = (args.symbol or "BTCUSDT").strip().upper()
    category = (args.category or "linear").strip()
    interval = str(args.interval or "15").strip()
    limit = int(args.limit or 200)
    if limit < 50:
        limit = 50
    if limit > 1000:
        limit = 1000

    url = f"{base_url}/v5/market/kline?category={category}&symbol={symbol}&interval={interval}&limit={limit}"
    raw = _http_get_json(url)
    candles = _parse_kline_list(raw)

    closes = [c["close"] for c in candles]
    sma20 = _compute_sma(closes, 20)
    sma50 = _compute_sma(closes, 50)
    rsi14 = _compute_rsi_wilder(closes, 14)

    last = candles[-1] if candles else None
    data: Dict[str, Any] = {
        "mode": "read_only",
        "note": "Analysis is computed from public candles only. No auth. No orders.",
        "settings": settings,
        "public": {
            "base_url": base_url,
            "kline": {
                "ok": raw.get("ok") if isinstance(raw, dict) else False,
                "status": raw.get("status") if isinstance(raw, dict) else None,
                "url": raw.get("url") if isinstance(raw, dict) else url,
            },
        },
        "query": {"category": category, "symbol": symbol, "interval": interval, "limit": limit},
        "candles_count": len(candles),
        "last_candle": last,
        "indicators": {
            "sma20": sma20,
            "sma50": sma50,
            "rsi14": rsi14,
        },
    }

    res = ControllerResult(ok=True, command="analyze", ts=_utc_iso(), data=data)
    _print_json(asdict(res))
    return 0


def _validate_side(side: str) -> str:
    s = side.strip().lower()
    if s not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")
    return s


def _validate_symbol(symbol: str) -> str:
    sym = symbol.strip().upper()
    if not sym or len(sym) < 3:
        raise ValueError("symbol looks invalid")
    return sym


def _validate_qty(qty: float) -> float:
    if qty <= 0:
        raise ValueError("qty must be > 0")
    return float(qty)


def cmd_dry_run(args: argparse.Namespace) -> int:
    try:
        symbol = _validate_symbol(args.symbol)
        side = _validate_side(args.side)
        qty = _validate_qty(args.qty)

        data: Dict[str, Any] = {
            "mode": "dry_run",
            "intent": {"symbol": symbol, "side": side, "qty": qty, "type": args.type},
            "execute": False,
            "note": "No order executed. This is a simulation output only.",
            "settings": _load_settings_summary(),
        }

        res = ControllerResult(ok=True, command="dry_run", ts=_utc_iso(), data=data)
        _print_json(asdict(res))
        return 0

    except Exception as e:
        res = ControllerResult(ok=False, command="dry_run", ts=_utc_iso(), data={}, error=f"{type(e).__name__}: {e}")
        _print_json(asdict(res))
        return 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="controller_cli", add_help=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("healthcheck", help="runtime/import/config checks")
    h.set_defaults(func=cmd_healthcheck)

    s = sub.add_parser("get_state", help="public read-only exchange state (safe)")
    s.add_argument("--symbol", default="BTCUSDT", help="ticker symbol (default BTCUSDT)")
    s.add_argument("--category", default="linear", help="bybit category (default linear)")
    s.set_defaults(func=cmd_get_state)

    c = sub.add_parser("get_candles", help="public read-only candles (kline)")
    c.add_argument("--symbol", default="BTCUSDT", help="ticker symbol (default BTCUSDT)")
    c.add_argument("--category", default="linear", help="bybit category (default linear)")
    c.add_argument("--interval", default="15", help="kline interval (e.g. 1,3,5,15,30,60,240, D)")
    c.add_argument("--limit", type=int, default=200, help="number of candles (max 1000)")
    c.set_defaults(func=cmd_get_candles)

    a = sub.add_parser("analyze", help="compute SMA/RSI from public candles (read-only)")
    a.add_argument("--symbol", default="BTCUSDT", help="ticker symbol (default BTCUSDT)")
    a.add_argument("--category", default="linear", help="bybit category (default linear)")
    a.add_argument("--interval", default="15", help="kline interval (e.g. 1,3,5,15,30,60,240, D)")
    a.add_argument("--limit", type=int, default=200, help="number of candles (min 50, max 1000)")
    a.set_defaults(func=cmd_analyze)

    d = sub.add_parser("dry_run", help="simulate an order intent (no execution)")
    d.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    d.add_argument("--side", required=True, help="buy|sell")
    d.add_argument("--qty", required=True, type=float, help="positive quantity")
    d.add_argument("--type", default="market", help="order type label for logging")
    d.set_defaults(func=cmd_dry_run)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
