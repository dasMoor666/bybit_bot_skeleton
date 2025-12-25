from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np

@dataclass
class Indicators:
    sma20: Optional[float]
    sma50: Optional[float]
    rsi14: Optional[float]

def sma(values: np.ndarray, period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return float(np.mean(values[-period:]))

def rsi(values: np.ndarray, period: int = 14) -> Optional[float]:
    if len(values) < period + 1:
        return None
    delta = np.diff(values)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))

def compute_indicators(candles: List[Dict[str, Any]]) -> Indicators:
    closes = np.array([float(c["close"]) for c in candles], dtype=float)
    return Indicators(
        sma20=sma(closes, 20),
        sma50=sma(closes, 50),
        rsi14=rsi(closes, 14),
    )

def simple_signal(ind: Indicators) -> Dict[str, Any]:
    # NO-TRADE signal suggestion only (intent)
    if ind.sma20 is None or ind.sma50 is None or ind.rsi14 is None:
        return {"signal": "HOLD", "reason": "not_enough_data"}

    # very simple rules (placeholder)
    if ind.sma20 > ind.sma50 and ind.rsi14 < 70:
        return {"signal": "BUY", "reason": "sma20_gt_sma50_and_rsi_ok"}
    if ind.sma20 < ind.sma50 and ind.rsi14 > 30:
        return {"signal": "SELL", "reason": "sma20_lt_sma50_and_rsi_ok"}
    return {"signal": "HOLD", "reason": "no_edge"}
