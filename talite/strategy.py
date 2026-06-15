"""Momentum signal engine - the core, rule-based decision.

The idea is deliberately simple: trade with the trend. Score a few momentum and
trend checks, and act when they line up. Strength gets bought, weakness gets
sold. Stops come off ATR; targets are a fixed multiple of the stop distance so
every trade carries a 1:2 risk/reward.

This same function drives both the live agent and the backtest, so what you test
is what you trade.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import indicators as ind

# Need enough bars for the 63-day (≈3 month) return and the 50-day average.
MIN_BARS = 70


@dataclass
class Signal:
    ticker: str
    action: str            # BUY | SELL | HOLD
    price: float
    stop: float
    target: float
    rr: float
    momentum: float        # net score, roughly -6..+6
    reasons: list[str] = field(default_factory=list)
    features: dict = field(default_factory=dict)


def features(df) -> dict:
    close = df["Close"]
    line, sig, hist = ind.macd(close)
    return {
        "close": float(close.iloc[-1]),
        "sma20": float(ind.sma(close, 20).iloc[-1]),
        "sma50": float(ind.sma(close, 50).iloc[-1]),
        "rsi": float(ind.rsi(close).iloc[-1]),
        "macd_hist": float(hist.iloc[-1]),
        "roc20": float(ind.roc(close, 20).iloc[-1]),
        "ret_1m": float(close.pct_change(21).iloc[-1]),
        "ret_3m": float(close.pct_change(63).iloc[-1]),
        "atr": float(ind.atr(df).iloc[-1]),
    }


def momentum_score(f: dict) -> float:
    """Six trend/momentum checks, each +1 bullish / -1 bearish."""
    s = 0.0
    s += 1 if f["close"] > f["sma20"] else -1
    s += 1 if f["sma20"] > f["sma50"] else -1
    s += 1 if f["ret_1m"] > 0 else -1
    s += 1 if f["ret_3m"] > 0 else -1
    s += 1 if f["macd_hist"] > 0 else -1
    s += 1 if f["roc20"] > 0 else -1
    return s


def _reasons(f: dict, score: float) -> list[str]:
    out = [f"momentum score {score:+.0f}/6"]
    out.append("above 20d" if f["close"] > f["sma20"] else "below 20d")
    out.append("uptrend (20>50)" if f["sma20"] > f["sma50"] else "downtrend (20<50)")
    out.append(f"1m {f['ret_1m']*100:+.1f}%, 3m {f['ret_3m']*100:+.1f}%")
    out.append(f"RSI {f['rsi']:.0f}")
    out.append("MACD up" if f["macd_hist"] > 0 else "MACD down")
    return out


def _levels(price, atr, action, rr, atr_mult):
    if action == "BUY":
        stop = price - atr_mult * atr
        return stop, price + rr * (price - stop)
    if action == "SELL":
        stop = price + atr_mult * atr
        return stop, price - rr * (stop - price)
    return float("nan"), float("nan")


def generate_signal(df, ticker: str = "", rr: float = 2.0,
                    atr_mult: float = 2.0) -> Signal:
    """Decide BUY / SELL / HOLD from the trailing price window."""
    if len(df) < MIN_BARS:
        return Signal(ticker, "HOLD", float(df["Close"].iloc[-1]),
                      float("nan"), float("nan"), rr, 0.0, ["not enough history"])

    f = features(df)
    score = momentum_score(f)

    # Ride strength, cut weakness. Skip blow-off-top RSI for new longs.
    if score >= 3 and f["rsi"] < 82:
        action = "BUY"
    elif score <= -3:
        action = "SELL"
    else:
        action = "HOLD"

    stop, target = _levels(f["close"], f["atr"], action, rr, atr_mult)
    return Signal(ticker, action, f["close"], stop, target, rr, score,
                  _reasons(f, score), f)


# --- Alpha registry ---------------------------------------------------------
# An "alpha" is any function with the signature
#     (df, ticker, rr, atr_mult) -> Signal
# Register your own and pick it with `--alpha NAME` on the CLI, or pass
# signal_fn=... to Agent / run_backtest. The built-in momentum engine above is
# just the default - drop your edge in beside it and trade it the same day.
#
#     from talite.strategy import register_alpha, Signal
#
#     @register_alpha("mean_reversion")
#     def my_alpha(df, ticker="", rr=2.0, atr_mult=2.0) -> Signal:
#         ...   # return a Signal with action / price / stop / target
#
ALPHAS: dict = {}


def register_alpha(name: str):
    def deco(fn):
        ALPHAS[name] = fn
        return fn
    return deco


def get_alpha(name: str):
    if name not in ALPHAS:
        raise KeyError(f"unknown alpha '{name}'. registered: {sorted(ALPHAS)}")
    return ALPHAS[name]


register_alpha("momentum")(generate_signal)
