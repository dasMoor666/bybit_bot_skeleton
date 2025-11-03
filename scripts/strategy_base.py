# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class Signal:
    def __init__(self, side:str, price:float, size:float, sl:float, tp:float, note:str=""):
        self.side = side        # "Buy" oder "Sell"
        self.price = price
        self.size = size
        self.sl = sl
        self.tp = tp
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        return {"side": self.side, "price": self.price, "size": self.size,
                "sl": self.sl, "tp": self.tp, "note": self.note}

class IStrategy(ABC):
    @abstractmethod
    def generate(self, klines:List[Dict[str,Any]], state:Dict[str,Any]) -> Optional[Signal]:
        """Gibt ein Signal zurück oder None."""
        ...

def atr(kl:List[Dict[str,Any]], n:int=14) -> float:
    import math
    trs=[]
    for i in range(1, min(len(kl), n+1)):
        h=float(kl[-i]["high"]); l=float(kl[-i]["low"])
        pc=float(kl[-i-1]["close"])
        tr=max(h-l, abs(h-pc), abs(l-pc))
        trs.append(tr)
    return sum(trs)/len(trs) if trs else 0.0
