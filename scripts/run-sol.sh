#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
export SYM=SOLUSDT
export TF=3
export LOOKBACK=2
export USE_PREV_CLOSE=1
export EPS_BREAK=0.0001
export MIN_RANGE=0
mkdir -p runs
.venv/bin/python scripts/run_signal_exec.py 2>&1 | tee -a runs/$(date +%F_%H%M)_${SYM}_TF${TF}.log
