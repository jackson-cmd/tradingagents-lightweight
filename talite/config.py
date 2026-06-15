"""Configuration and defaults.

Everything here can be overridden with environment variables (see .env.example)
or by passing arguments on the command line. Defaults are chosen so the tool
runs out of the box with no API keys at all (rule-based mode).
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _f(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return float(default)


# Optional market-news RSS feed (titles only). Empty by default; set it to use
# the "rss" news source.
RSS_FEED_URL = os.getenv("RSS_FEED_URL", "")
# Which news source to read: sec (free, default) | benzinga (paid) | rss.
NEWS_SOURCE = os.getenv("NEWS_SOURCE", "sec")

# LLM. Empty/absent keys just fall back to the rule engine.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")

# Trade construction.
RISK_REWARD = _f("RISK_REWARD", 2.0)        # fixed 1:2
ATR_MULT = _f("ATR_MULT", 2.0)              # stop = entry -/+ ATR_MULT * ATR
RISK_PER_TRADE = _f("RISK_PER_TRADE", 0.01)  # 1% of equity at risk per position

# How much history to pull. Live analysis wants ~1y so the 50d/63d windows fill.
LIVE_PERIOD = os.getenv("LIVE_PERIOD", "1y")

# Default basket for `backtest` when no tickers are passed.
DEFAULT_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AMD",
]

RESULTS_DIR = os.getenv("RESULTS_DIR", "results")
