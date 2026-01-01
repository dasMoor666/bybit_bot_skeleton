from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Any, Dict

from src.controller.cli import ControllerResult, _utc_iso, _print_json

def run(args: argparse.Namespace) -> int:
    # HARD BLOCK in Phase 0: no live order execution.
    data: Dict[str, Any] = {
        "mode": "blocked",
        "reason": "place_order is disabled in Phase 0 (Safety Gate). Use dry_run to log intents only.",
        "hint": "If you later enable execution, it must pass SAFETY_GATES.md and require explicit unlock.",
        "args_present": sorted(list(vars(args).keys())) if hasattr(args, "__dict__") else [],
    }
    res = ControllerResult(ok=False, command="place_order", ts=_utc_iso(), data=data, error="BLOCKED_PHASE0")
    _print_json(asdict(res))
    return 2
