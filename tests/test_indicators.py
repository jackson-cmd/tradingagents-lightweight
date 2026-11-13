"""The indicators on series whose answers are known by hand."""

import numpy as np
import pandas as pd

from talite import indicators as ind


def zigzag(up: float, down: float, n: int = 120, start: float = 100.0) -> pd.Series:
    return pd.Series(start + np.cumsum(np.tile([up, down], n // 2)))


def test_sma_and_rate_of_change_on_a_straight_line():
    s = pd.Series(np.arange(1.0, 31.0))
    assert ind.sma(s, 5).iloc[-1] == 28.0                       # mean of 26..30
    assert abs(ind.roc(s, 10).iloc[-1] - 50.0) < 1e-9           # 30 / 20 - 1 = 50%


def test_rsi_is_high_when_gains_outweigh_losses_and_low_otherwise():
    assert ind.rsi(zigzag(3.0, -1.0)).iloc[-1] > 70             # average gain about 3x the average loss
    assert ind.rsi(zigzag(-3.0, 1.0, start=400.0)).iloc[-1] < 30


def test_atr_of_a_constant_two_point_range():
    close = pd.Series(np.full(40, 100.0))
    bars = pd.DataFrame({"High": close + 1, "Low": close - 1, "Close": close})
    assert abs(ind.atr(bars).iloc[-1] - 2.0) < 1e-9


def test_macd_histogram_is_positive_when_the_trend_speeds_up():
    s = pd.Series(100 + np.arange(80) ** 1.5)
    _, _, hist = ind.macd(s)
    assert hist.iloc[-1] > 0
