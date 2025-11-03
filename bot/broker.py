from dataclasses import dataclass
from datetime import datetime, timezone
from loguru import logger
import csv, os
from .config import SETTINGS

@dataclass
class Position:
    side: str  # 'LONG' or 'SHORT'
    qty: float
    entry_price: float
    ts_open: datetime
    bars_open: int = 0

class Broker:
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)
        self.position: Position | None = None
        self.equity = 10_000.0  # virtual equity for DRY_RUN
        self.daily_start_equity = self.equity
        self._init_logs()

        if not SETTINGS.dry_run:
            # TODO: REAL ORDER - init pybit client for Testnet
            pass

    def _init_logs(self):
        self.runtime_log = os.path.join(self.logs_dir, "runtime.log")
        logger.add(self.runtime_log, rotation="5 MB")
        self.trades_file = os.path.join(self.logs_dir, "trades.csv")
        self.orders_file = os.path.join(self.logs_dir, "orders.csv")
        self.equity_file = os.path.join(self.logs_dir, "equity_curve.csv")
        if not os.path.exists(self.trades_file):
            with open(self.trades_file, "w", newline="") as f:
                csv.writer(f).writerow(["ts_open","ts_close","side","entry_price","exit_price","size","fee","pnl_abs","pnl_pct","max_fav_pct","max_adv_pct","bars_open","reason"])
        if not os.path.exists(self.orders_file):
            with open(self.orders_file, "w", newline="") as f:
                csv.writer(f).writerow(["ts","type","side","price","qty","note"])
        if not os.path.exists(self.equity_file):
            with open(self.equity_file, "w", newline="") as f:
                csv.writer(f).writerow(["ts","equity"])

    def log_equity(self):
        with open(self.equity_file, "a", newline="") as f:
            csv.writer(f).writerow([datetime.now(timezone.utc).isoformat(), f"{self.equity:.2f}"])

    # --- DRY RUN order simulation ---
    def open_market(self, side: str, price: float, qty: float):
        if self.position is not None:
            logger.warning("Position already open; skip open_market")
            return False
        self.position = Position(side=side, qty=qty, entry_price=price, ts_open=datetime.now(timezone.utc))
        with open(self.orders_file, "a", newline="") as f:
            csv.writer(f).writerow([datetime.now(timezone.utc).isoformat(), "OPEN", side, price, qty, "dry_run"])
        logger.info(f"Opened {side} qty={qty} price={price}")
        return True

    def close_market(self, reason: str, price: float):
        if self.position is None:
            return
        pos = self.position
        pnl_pct = (price - pos.entry_price)/pos.entry_price * 100.0 * (1 if pos.side=="LONG" else -1)
        pnl_abs = self.equity * (pnl_pct/100.0)
        fee = abs(pnl_abs) * 0.000  # fee simplified; set if wanted
        self.equity += (pnl_abs - fee)
        with open(self.trades_file, "a", newline="") as f:
            csv.writer(f).writerow([
                pos.ts_open.isoformat(),
                datetime.now(timezone.utc).isoformat(),
                pos.side, f"{pos.entry_price:.2f}", f"{price:.2f}", pos.qty, f"{fee:.2f}", f"{pnl_abs:.2f}", f"{pnl_pct:.3f}", "", "", pos.bars_open, reason
            ])
        with open(self.orders_file, "a", newline="") as f:
            csv.writer(f).writerow([datetime.now(timezone.utc).isoformat(), "CLOSE", pos.side, price, pos.qty, reason])
        logger.info(f"Closed {pos.side} at {price} reason={reason} PnL%={pnl_pct:.3f}")
        self.position = None
        self.log_equity()

    def tick_bar(self):
        if self.position:
            self.position.bars_open += 1

    # --- Real order stubs ---
    # Implementiere hier echte pybit REST/WS Calls, wenn DRY_RUN=false
