# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Optional, List
import os

from scripts.strategy_base import IStrategy, Signal, atr

class MomScalp(IStrategy):
    """
    Momentum-Breakout mit:
      - strikter Breakout-Logik (strict > / <)
      - Range-Guard (MIN_RANGE)
      - Tie-Handling (TIE_SIDE=Long|Short)
      - optionale Nutzung des vorigen Closes (USE_PREV_CLOSE)
    ENV-Variablen (werden im run_script geladen):
      LOOKBACK, EPS_BREAK, USE_PREV_CLOSE, ALLOW_SHORT, DEBUG,
      MIN_RANGE, TIE_SIDE
    """

    def __init__(
        self,
        lookback: int = 20,
        vol_mult: float = 0.0,
        atr_mult_sl: float = 0.0,
        atr_mult_tp: float = 0.0,
        qty: float = 0.001,
        allow_short: bool = False,
        debug: bool = False,
        eps_break: float = 0.0,
        use_prev_close: bool = False
    ):
        self.lookback = int(lookback)
        self.vol_mult = float(vol_mult)
        self.atr_mult_sl = float(atr_mult_sl)
        self.atr_mult_tp = float(atr_mult_tp)
        self.qty = float(qty)
        self.allow_short = bool(allow_short)
        self.debug = bool(debug)
        self.eps_break = float(eps_break)
        self.use_prev_close = bool(use_prev_close)

    # --- Hilfsfunktionen für N-High/Low über abgeschlossene Kerzen ---
    def _high(self, kl: List[Dict[str, Any]], n: int) -> float:
        # N abschlossene Kerzen (exkl. laufende)
        return max(float(k["high"]) for k in kl[-n-1:-1])

    def _low(self, kl: List[Dict[str, Any]], n: int) -> float:
        return min(float(k["low"]) for k in kl[-n-1:-1])

    def generate(self, klines: List[Dict[str, Any]], state: Optional[Dict[str, Any]] = None) -> Optional[Signal]:
        if state is None:
            state = {}

        n = int(self.lookback)
        if len(klines) < (n + 2):
            if self.debug:
                state.setdefault("__debug__", {}).update({
                    "reason": "not_enough_bars",
                    "bars": len(klines)
                })
            return None

        last = klines[-1]         # laufende Kerze
        prev = klines[-2]         # letzte abgeschlossene Kerze
        ref  = prev if self.use_prev_close else last

        # Basisdaten
        px   = float(ref["close"])
        hiN  = self._high(klines, n)
        loN  = self._low(klines, n)
        a14  = atr(klines, 14)

        # Debug-Infos
        if self.debug:
            lv   = float(prev["volume"])
            avgv = sum(float(k["volume"]) for k in klines[-n-1:-1]) / float(n)
            state.setdefault("__debug__", {}).update({
                "px": px, "hiN": hiN, "loN": loN,
                "atr14": a14,
                "use_prev_close": self.use_prev_close,
                "eps_break": self.eps_break,
                "vol_prev": lv, "vol_avg": avgv,
            })

        # --- Range-Guard ---
        min_range = float(os.environ.get("MIN_RANGE", "0"))
        rng = hiN - loN
        if rng < min_range:
            if self.debug:
                state.setdefault("__debug__", {}).update({
                    "reason": "range_too_small", "rng": rng, "min_range": min_range
                })
            return None

        # --- Breakout-Logik (strict) ---
        eps = float(self.eps_break)
        long_break  = px >  hiN * (1.0 + eps)
        short_break = px <  loN * (1.0 - eps)

        # Tie-Handling
        if long_break and short_break:
            tie_side = os.environ.get("TIE_SIDE", "").lower()
            if tie_side == "long":
                long_break, short_break = True, False
            elif tie_side == "short":
                long_break, short_break = False, True
            else:
                if self.debug:
                    state.setdefault("__debug__", {}).update({"reason": "tie_no_preference"})
                return None

        if not long_break and not short_break:
            if self.debug:
                state.setdefault("__debug__", {}).update({"reason":"no_break"})
            return None

        # Short erlaubt?
        if short_break and not self.allow_short:
            if self.debug:
                state.setdefault("__debug__", {}).update({"reason":"short_not_allowed"})
            return None

        # --- einfache TP/SL-Geometrie (konstant/robust) ---
        # Du kannst das später durch ATR/Settings ersetzen.
        tp_dist = max(px * 0.007, rng * 0.50)  # 0.7% oder halbe Range
        sl_dist = max(px * 0.004, rng * 0.30)  # 0.4% oder 30% der Range

        if long_break:
            side = "Buy"
            tp = px + tp_dist
            sl = px - sl_dist
        else:
            side = "Sell"
            tp = px - tp_dist
            sl = px + sl_dist

        return Signal(
            side=side,
            price=px,
            size=self.qty,
            sl=sl,
            tp=tp,
            note=f"mom_s break n={n} eps={eps} rng={rng}"
        )
