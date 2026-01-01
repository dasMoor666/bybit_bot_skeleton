from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np

@dataclass
class Indicators:
    sma20: Optional[float]
    sma50: Optional[float]
    rsi14: Optional[float]

def _to_closes(candles: List[Dict[str, Any]]) -> List[float]:
    closes: List[float] = []
    for c in candles or []:
        try:
            closes.append(float(c["close"]))
        except Exception:
            continue
    return closes

def _sma(values: List[float], n: int) -> Optional[float]:
    if n <= 0 or len(values) < n:
        return None
    return float(np.mean(values[-n:]))

def _rsi_wilder(closes: List[float], period: int = 14) -> Optional[float]:
    if period <= 0 or len(closes) < period + 1:
        return None
    deltas = np.diff(np.array(closes, dtype=float))
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Wilder smoothing
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))

def compute_indicators(candles: List[Dict[str, Any]]) -> Indicators:
    closes = _to_closes(candles)
    return Indicators(
        sma20=_sma(closes, 20),
        sma50=_sma(closes, 50),
        rsi14=_rsi_wilder(closes, 14),
    )

def simple_signal(ind: Indicators) -> str:
    # Conservative, deterministic rule (NO-TRADE system can log it)
    if ind.sma20 is None or ind.sma50 is None or ind.rsi14 is None:
        return "HOLD"
    if ind.sma20 > ind.sma50 and ind.rsi14 < 70:
        return "LONG_BIAS"
    if ind.sma20 < ind.sma50 and ind.rsi14 > 30:
        return "SHORT_BIAS"
    return "HOLD"
