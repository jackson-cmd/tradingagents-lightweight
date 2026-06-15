"""Backtest a basket over the last month. Runs from the repo without installing.

    python examples/run_backtest.py AAPL MSFT NVDA
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from talite import run_backtest

tickers = [a for a in sys.argv[1:] if not a.startswith("-")] or None
res = run_backtest(tickers=tickers, months=1)
for k, v in res.metrics.items():
    print(f"{k:14}: {v}")
