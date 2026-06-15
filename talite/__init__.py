"""TradingAgents-Lightweight - a fast, cheap, momentum-first swing trader.

    from talite import Agent
    Agent(use_llm=False).analyze("AAPL")
"""
from .agent import Agent, Decision
from .backtest import BacktestResult, run_backtest
from .execution import Order, get_broker, order_from_decision
from .news import get_news
from .screener import momentum_tickers, screen_momentum
from .strategy import Signal, generate_signal, register_alpha

__version__ = "0.1.0"
__all__ = [
    "Agent", "Decision", "Signal", "generate_signal", "register_alpha",
    "run_backtest", "BacktestResult",
    "screen_momentum", "momentum_tickers",
    "get_news",
    "Order", "order_from_decision", "get_broker",
    "__version__",
]
