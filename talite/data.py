"""Data access: prices (yfinance), fundamentals (Finviz), news (RSS).

Every fetch degrades gracefully. If Finviz or the feed is down, you still get a
decision from price action alone - the point is to keep moving, not to block.
"""
from __future__ import annotations

import feedparser
import pandas as pd
import yfinance as yf

from .config import RSS_FEED_URL

PRICE_COLS = ["Open", "High", "Low", "Close", "Volume"]


def _flatten(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    return df


def get_prices(ticker: str, start: str | None = None, period: str = "1y",
               interval: str = "1d") -> pd.DataFrame:
    """Daily OHLCV. Pass `start` (YYYY-MM-DD) for an exact window, else `period`."""
    t = yf.Ticker(ticker)
    df = (t.history(start=start, interval=interval, auto_adjust=True)
          if start else
          t.history(period=period, interval=interval, auto_adjust=True))
    if df is None or df.empty:
        raise ValueError(f"no price data for {ticker}")
    df = _flatten(df)
    return df[PRICE_COLS].dropna()


def get_fundamentals(ticker: str) -> dict:
    """A handful of Finviz fields. Returns {} on any failure."""
    try:
        from finvizfinance.quote import finvizfinance
        return finvizfinance(ticker).ticker_fundament() or {}
    except Exception:
        return {}


def get_market_news(limit: int = 40, url: str = RSS_FEED_URL) -> list[dict]:
    """Latest market headlines from an RSS feed. No URL configured -> []."""
    if not url:
        return []
    try:
        feed = feedparser.parse(url)
        return [
            {"title": e.get("title", ""), "published": e.get("published", "")}
            for e in feed.entries[:limit]
        ]
    except Exception:
        return []
