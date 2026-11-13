"""The momentum rule on made-up price paths: buy a steady uptrend, sell a downtrend, wait without enough history."""

import numpy as np
import pandas as pd

from talite.strategy import MIN_BARS, generate_signal


def bars(up: float, down: float, n: int = 150, start: float = 200.0) -> pd.DataFrame:
    close = start + np.cumsum(np.tile([up, down], n // 2))
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1_000_000})


def test_an_uptrend_buys_with_the_stop_below_and_a_one_to_two_target():
    s = generate_signal(bars(2.0, -1.0), "TEST")
    assert s.action == "BUY" and s.momentum >= 3
    assert s.stop < s.price < s.target
    assert abs((s.target - s.price) - 2 * (s.price - s.stop)) < 1e-9


def test_a_downtrend_sells():
    s = generate_signal(bars(-2.0, 1.0), "TEST")
    assert s.action == "SELL" and s.target < s.price < s.stop


def test_short_history_holds():
    s = generate_signal(bars(2.0, -1.0, n=MIN_BARS - 10), "TEST")
    assert s.action == "HOLD"
