#!/usr/bin/env bash
set -euo pipefail
# Aus dem Projekt-Root starten
cd "$(dirname "$0")/.."
PYTHONPATH=. ./scripts/panic_flat.py
