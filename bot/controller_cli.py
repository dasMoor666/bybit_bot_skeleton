#!/usr/bin/env python3

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def utc_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def out(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


def bool_env(name):
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return None


def settings_summary():
    summary = {
        "config_loaded": False,
        "settings_class": None,
        "env_flags": {
            "DRY_RUN": bool_env("DRY_RUN"),
            "EXECUTE": bool_env("EXECUTE"),
            "TESTNET": bool_env("TESTNET"),
        },
        "secrets_present": {
            "BYBIT_API_KEY": bool(os.getenv("BYBIT_API_KEY")),
            "BYBIT_API_SECRET": bool(os.getenv("BYBIT_API_SECRET")),
            "API_KEY": bool(os.getenv("API_KEY")),
            "API_SECRET": bool(os.getenv("API_SECRET")),
        },
    }

    try:
        from bot.config import Settings
        s = Settings()
        summary["config_loaded"] = True
        summary["settings_class"] = "bot.config.Settings"
        # only harmless fields if they exist
        for field in ["mode", "env", "exchange", "base_url", "testnet"]:
            if hasattr(s, field):
                val = getattr(s, field)
                summary[field] = val if isinstance(val, (str, int, float, bool)) or val is None else str(val)
    except Exception as e:
        summary["config_error"] = f"{type(e).__name__}: {e}"

    return summary


def cmd_healthcheck(_args):
    data = {
        "python": sys.version.split()[0],
        "cwd": os.getcwd(),
        "settings": settings_summary(),
        "imports": {},
    }
    for mod in ["bot", "bot.config", "bot.run"]:
        try:
            __import__(mod)
            data["imports"][mod] = True
        except Exception as e:
            data["imports"][mod] = f"{type(e).__name__}: {e}"

    out({"ok": True, "command": "healthcheck", "ts": utc_iso(), "data": data})
    return 0


def cmd_get_state(_args):
    out({
        "ok": True,
        "command": "get_state",
        "ts": utc_iso(),
        "data": {
            "mode": "read_only",
            "note": "Phase 0B placeholder (no exchange wiring).",
            "settings": settings_summary(),
        },
    })
    return 0


def cmd_dry_run(args):
    try:
        symbol = args.symbol.strip().upper()
        side = args.side.strip().lower()
        qty = float(args.qty)
        if not symbol or len(symbol) < 3:
            raise ValueError("symbol looks invalid")
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        if qty <= 0:
            raise ValueError("qty must be > 0")

        out({
            "ok": True,
            "command": "dry_run",
            "ts": utc_iso(),
            "data": {
                "mode": "dry_run",
                "execute": False,
                "intent": {"symbol": symbol, "side": side, "qty": qty, "type": args.type},
                "note": "No order executed (simulation only).",
                "settings": settings_summary(),
            },
        })
        return 0
    except Exception as e:
        out({"ok": False, "command": "dry_run", "ts": utc_iso(), "error": f"{type(e).__name__}: {e}", "data": {}})
        return 2


def main(argv=None):
    p = argparse.ArgumentParser(prog="controller_cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("healthcheck")
    h.set_defaults(func=cmd_healthcheck)

    s = sub.add_parser("get_state")
    s.set_defaults(func=cmd_get_state)

    d = sub.add_parser("dry_run")
    d.add_argument("--symbol", required=True)
    d.add_argument("--side", required=True)
    d.add_argument("--qty", required=True)
    d.add_argument("--type", default="market")
    d.set_defaults(func=cmd_dry_run)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
