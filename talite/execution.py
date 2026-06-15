"""Execution - turn a decision into a sized order and route it.

Default is paper: the order is sized off your risk budget, printed, and logged to
results/paper_orders.csv. Nothing leaves your machine.

Live routing is opt-in and uses the broker's own SDK + your keys. The Alpaca
adapter places a one-shot bracket (entry + 1:2 take-profit + stop), which is
exactly how this strategy is meant to trade. It defaults to the paper endpoint -
you have to ask for live explicitly.
"""
from __future__ import annotations

import csv
import os
from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class Order:
    ticker: str
    side: str          # buy | sell
    qty: int
    entry: float
    stop: float
    target: float
    rr: float
    notional: float


def size_position(entry: float, stop: float, equity: float,
                  risk_per_trade: float = 0.01) -> int:
    """Shares such that a stop-out loses exactly `risk_per_trade` of equity."""
    risk_per_share = abs(entry - stop)
    if risk_per_share <= 0:
        return 0
    return int((equity * risk_per_trade) // risk_per_share)


def order_from_decision(decision, equity: float = 10_000,
                        risk_per_trade: float = 0.01) -> Order | None:
    if decision.action not in ("BUY", "SELL"):
        return None
    qty = size_position(decision.price, decision.stop, equity, risk_per_trade)
    if qty <= 0:
        return None
    side = "buy" if decision.action == "BUY" else "sell"
    return Order(decision.ticker, side, qty, round(decision.price, 2),
                 round(decision.stop, 2), round(decision.target, 2),
                 round(decision.rr, 1), round(qty * decision.price, 2))


class PaperBroker:
    """Logs orders to a CSV. No network, no risk - the default."""
    name = "paper"

    def __init__(self, out_dir: str = "results"):
        self.out_dir = out_dir

    def submit(self, order: Order) -> dict:
        os.makedirs(self.out_dir, exist_ok=True)
        path = os.path.join(self.out_dir, "paper_orders.csv")
        fresh = not os.path.exists(path)
        with open(path, "a", newline="") as fh:
            w = csv.writer(fh)
            if fresh:
                w.writerow(["ts", "ticker", "side", "qty", "entry", "stop",
                            "target", "notional"])
            w.writerow([datetime.now().isoformat(timespec="seconds"), order.ticker,
                        order.side, order.qty, order.entry, order.stop,
                        order.target, order.notional])
        return {"status": "accepted", "broker": "paper", **asdict(order)}


class AlpacaBroker:
    """Live/paper bracket orders via alpaca-py. Opt-in: `pip install alpaca-py`
    and set ALPACA_API_KEY / ALPACA_SECRET_KEY. Defaults to the paper endpoint."""
    name = "alpaca"

    def __init__(self, paper: bool = True):
        from alpaca.trading.client import TradingClient
        key, sec = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
        if not (key and sec):
            raise RuntimeError("set ALPACA_API_KEY and ALPACA_SECRET_KEY")
        self.client = TradingClient(key, sec, paper=paper)
        self.paper = paper

    def submit(self, order: Order) -> dict:
        from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
        from alpaca.trading.requests import (MarketOrderRequest,
                                             StopLossRequest, TakeProfitRequest)
        req = MarketOrderRequest(
            symbol=order.ticker, qty=order.qty,
            side=OrderSide.BUY if order.side == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.GTC, order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=order.target),
            stop_loss=StopLossRequest(stop_price=order.stop))
        res = self.client.submit_order(req)
        return {"status": "submitted", "id": str(res.id),
                "broker": f"alpaca ({'paper' if self.paper else 'LIVE'})",
                **asdict(order)}


def get_broker(name: str = "paper", live: bool = False, out_dir: str = "results"):
    name = (name or "paper").lower()
    if name == "alpaca":
        return AlpacaBroker(paper=not live)
    return PaperBroker(out_dir=out_dir)
