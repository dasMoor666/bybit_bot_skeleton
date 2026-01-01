from __future__ import annotations
import argparse

# Wrapper: reuse existing logic still in cli.py (Phase 0 safe, no re-implementation risk)
from src.controller import cli as _cli

def run(args: argparse.Namespace) -> int:
    if hasattr(_cli, "cmd_get_private_state"):
        return _cli.cmd_get_private_state(args)  # type: ignore
    raise RuntimeError("cmd_get_private_state not found in src.controller.cli (expected in Phase 0)")
