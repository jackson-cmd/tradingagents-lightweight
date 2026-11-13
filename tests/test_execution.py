"""Position sizing and the paper broker: a stop-out costs exactly the risk budget, and nothing leaves the machine."""

from types import SimpleNamespace

from talite.execution import PaperBroker, get_broker, order_from_decision, size_position


def decision(action: str, price: float, stop: float, target: float) -> SimpleNamespace:
    return SimpleNamespace(action=action, ticker="TEST", price=price, stop=stop, target=target, rr=2.0)


def test_a_stop_out_loses_the_risk_budget():
    # $10,000 equity at 1% risk is $100; a $2 stop distance allows 50 shares
    assert size_position(50.0, 48.0, 10_000, 0.01) == 50
    assert size_position(50.0, 50.0, 10_000, 0.01) == 0


def test_only_buy_and_sell_become_orders():
    order = order_from_decision(decision("BUY", 100.0, 96.0, 108.0), equity=10_000, risk_per_trade=0.01)
    assert (order.side, order.qty, order.notional) == ("buy", 25, 2500.0)
    short = order_from_decision(decision("SELL", 200.0, 210.0, 180.0))
    assert (short.side, short.qty) == ("sell", 10)
    assert order_from_decision(decision("HOLD", 100.0, 96.0, 108.0)) is None


def test_the_paper_broker_logs_to_a_csv(tmp_path):
    order = order_from_decision(decision("BUY", 100.0, 96.0, 108.0))
    result = get_broker("paper", out_dir=str(tmp_path)).submit(order)
    assert result["status"] == "accepted"
    rows = (tmp_path / "paper_orders.csv").read_text().splitlines()
    assert rows[0].startswith("ts,ticker,side,qty") and ",TEST,buy,25," in rows[1]
    PaperBroker(out_dir=str(tmp_path)).submit(order)
    assert len((tmp_path / "paper_orders.csv").read_text().splitlines()) == 3   # one header, then appended rows
