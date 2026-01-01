#!/usr/bin/env bash
set -euo pipefail
python -u src/controller/orchestration/loop_dry_run.py "$@"
