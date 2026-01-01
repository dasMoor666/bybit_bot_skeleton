from __future__ import annotations

import argparse
import os
import sys
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.controller.cli import ControllerResult, _load_settings_summary, _print_json  # reuse existing helpers

def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def run(_: argparse.Namespace) -> int:
    data: Dict[str, Any] = {
        "python": sys.version.split()[0],
        "cwd": os.getcwd(),
        "settings": _load_settings_summary(),
        "imports": {},
    }

    for mod in ["src", "src.controller", "src.controller.config"]:
        try:
            __import__(mod)
            data["imports"][mod] = True
        except Exception as e:
            data["imports"][mod] = f"{type(e).__name__}: {e}"

    res = ControllerResult(ok=True, command="healthcheck", ts=_utc_iso(), data=data)
    _print_json(asdict(res))
    return 0
