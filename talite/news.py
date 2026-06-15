"""Pluggable news sources.

SEC EDGAR 8-K filings are the default: free, no key, and the raw feed where
material events (M&A, splits, offerings, guidance) first show up officially.

Sources:
    sec      - SEC EDGAR latest 8-K filings, free, no key             (default)
    benzinga - Benzinga news API, real-time, per-ticker  (needs BENZINGA_API_KEY)
    rss      - any market-news RSS feed you point RSS_FEED_URL at

Each returns a list of {"title", "published", "source"} dicts. Add your own the
same way - one function, wired into get_news().
"""
from __future__ import annotations

import os

from . import data
from .config import RSS_FEED_URL


def get_news(source: str | None = None, limit: int = 40,
             tickers=None) -> list[dict]:
    source = (source or os.getenv("NEWS_SOURCE", "sec")).lower()
    if source == "benzinga":
        return _benzinga(limit, tickers)
    if source == "rss":
        return _rss(limit)
    return _sec(limit)


def _rss(limit: int) -> list[dict]:
    if not RSS_FEED_URL:
        return []
    return [{**h, "source": "rss"}
            for h in data.get_market_news(limit=limit, url=RSS_FEED_URL)]


def _benzinga(limit: int, tickers) -> list[dict]:
    """Benzinga news API. Real-time, per-ticker. https://www.benzinga.com/apis/"""
    import requests
    key = os.getenv("BENZINGA_API_KEY")
    if not key:
        raise RuntimeError("set BENZINGA_API_KEY (https://www.benzinga.com/apis/)")
    params = {"token": key, "pageSize": min(limit, 100), "displayOutput": "headline"}
    if tickers:
        params["tickers"] = ",".join(tickers) if isinstance(tickers, (list, tuple)) else tickers
    r = requests.get("https://api.benzinga.com/api/v2/news", params=params,
                     headers={"accept": "application/json"}, timeout=10)
    r.raise_for_status()
    items = r.json() or []
    return [{"title": it.get("title", ""), "published": it.get("created", ""),
             "source": "benzinga"} for it in items][:limit]


def _sec(limit: int) -> list[dict]:
    """SEC EDGAR latest 8-K filings (material events) - free, no key.
    8-Ks are where M&A, splits, offerings and the like first show up officially.
    SEC requires a descriptive User-Agent (override with SEC_USER_AGENT)."""
    import feedparser
    import requests
    ua = os.getenv("SEC_USER_AGENT", "tradingagents-lightweight research@example.com")
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K"
           f"&owner=include&count={min(limit, 100)}&output=atom")
    r = requests.get(url, headers={"User-Agent": ua}, timeout=10)
    r.raise_for_status()
    feed = feedparser.parse(r.text)
    return [{"title": e.get("title", ""), "published": e.get("updated", ""),
             "source": "sec"} for e in feed.entries[:limit]]
