"""Auto stock picker - let Finviz hand you the momentum, don't hunt for it.

The default filters define a universe of liquid, non-penny names in a confirmed
uptrend (price above the 20- and 50-day, up on the quarter). We then rank that
universe by a blended momentum score and hand back the leaders. These are the
"MU / SNDK"-type names that are actually moving, surfaced automatically.

Everything here is tunable. Swap the filters, change the weights, add your own
ranking - that is the whole point (see the alpha registry in strategy.py).
"""
from __future__ import annotations

import pandas as pd

# Server-side Finviz filters: the momentum universe before ranking.
MOMENTUM_FILTERS = {
    "Market Cap.": "+Mid (over $2bln)",
    "Average Volume": "Over 1M",
    "Price": "Over $10",
    "20-Day Simple Moving Average": "Price above SMA20",
    "50-Day Simple Moving Average": "Price above SMA50",
    "Performance": "Quarter Up",
}

PERF_COLS = ["Perf Week", "Perf Month", "Perf Quart"]


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def screen_momentum(top_n: int = 15, filters: dict | None = None,
                    include_overheated: bool = False) -> pd.DataFrame:
    """Return the top momentum names as a ranked DataFrame.

    The score rewards sustained (quarter) and recent (month) strength, with a
    small weekly kicker. By default it drops names already up >25% on the week,
    so you ride trends instead of chasing the last tick of a spike.
    """
    from finvizfinance.screener.performance import Performance

    fp = Performance()
    fp.set_filter(filters_dict=filters or MOMENTUM_FILTERS)
    df = fp.screener_view(order="Performance (Month)", ascend=False, verbose=0)
    if df is None or df.empty:
        return pd.DataFrame()

    for c in PERF_COLS:
        df[c] = _num(df[c])
    df = df.dropna(subset=PERF_COLS)

    if not include_overheated:
        df = df[df["Perf Week"] <= 0.25]

    df["momentum"] = (0.45 * df["Perf Month"]
                      + 0.40 * df["Perf Quart"]
                      + 0.15 * df["Perf Week"])
    df = df.sort_values("momentum", ascending=False).reset_index(drop=True)

    keep = ["Ticker", "Price", "Perf Week", "Perf Month", "Perf Quart",
            "Rel Volume", "momentum"]
    keep = [c for c in keep if c in df.columns]
    return df[keep].head(top_n)


def momentum_tickers(top_n: int = 15, **kwargs) -> list[str]:
    """Just the ticker list, ready to feed into analyze or backtest."""
    df = screen_momentum(top_n=top_n, **kwargs)
    return [] if df.empty else df["Ticker"].tolist()


def format_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "no names matched the screen"
    rows = ["  #  TICKER    PRICE   1W%    1M%    1Q%   relVol",
            "  " + "-" * 50]
    for i, r in df.iterrows():
        rows.append(
            f"  {i+1:<2} {r['Ticker']:<7} {r['Price']:>7.2f}  "
            f"{r['Perf Week']*100:>5.1f}  {r['Perf Month']*100:>5.1f}  "
            f"{r['Perf Quart']*100:>5.1f}  {r.get('Rel Volume', float('nan')):>5.2f}")
    return "\n".join(rows)
