#!/usr/bin/env python3
"""
Minimal Controller CLI (Phase 0B)
- healthcheck: runtime/import/config check
- get_state: READ-ONLY public Bybit GETs (no auth, no orders)
- dry_run: validate + log an order intent (no execution)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _print_json(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


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


def _http_get_json(url: str, timeout_s: int = 10) -> Dict[str, Any]:
    """Public GET helper. No auth. No secrets. SSL uses certifi if available."""
    try:
        import urllib.request
        import ssl

        # Robust SSL: prefer certifi CA bundle, fallback to system default
        try:
            import certifi  # type: gnore
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

    # Import probes (no side effects intended)
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

    # Decide public base URL (no auth)
    testnet_flag = None
    for key in ("bybit_testnet", "testnet"):
        if isinstance(settings.get(key), bool):
            testnet_flag = settings.get(key)
            break
    if testnet_flag is None:
        testnet_flag = settings.get("env_flags", {}).get("TESTNET") is True

    base_url = "https://api-testnet.bybit.com" if testnet_flag else "https://api.bybit.com"

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
