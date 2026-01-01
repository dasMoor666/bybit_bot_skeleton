from __future__ import annotations
import argparse

# Wrapper: reuse existing dry_run intent logger in cli.py
from src.controller import cli as _cli

def run(args: argparse.Namespace) -> int:
    if hasattr(_cli, "cmd_dry_run"):
        return _cli.cmd_dry_run(args)  # type: ignore
    raise RuntimeError("cmd_dry_run not found in src.controller.cli (expected in Phase 0)")
