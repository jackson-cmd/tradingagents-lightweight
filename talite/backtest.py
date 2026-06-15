"""Backtest the momentum engine over a recent window and save the results.

Design notes:
- Rule-based only. No LLM calls in the loop, so a full basket runs in seconds and
  costs nothing. The live agent can layer an LLM on top; the edge is the rules.
- No lookahead. The signal on bar i only sees data up to and including bar i, and
  the position is then managed from bar i+1 using that bar's high/low.
- Fixed-fractional risk: each trade risks `risk_per_trade` of current equity, so
  a 1:2 winner makes +2R and a stop-out loses -1R.
- When both stop and target fall inside the same bar, we assume the stop hit
  first. Pessimistic on purpose.

Outputs (under results/): trades CSV, equity CSV, summary JSON, equity+drawdown PNG.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import config, data
from .strategy import generate_signal, get_alpha

TRADING_DAYS_PER_MONTH = 21


@dataclass
class Trade:
    ticker: str
    side: str
    entry_date: str
    entry: float
    exit_date: str
    exit: float
    r_multiple: float
    pnl: float
    exit_reason: str


@dataclass
class BacktestResult:
    trades: list
    equity: "pd.Series"
    metrics: dict
    params: dict = field(default_factory=dict)


def _simulate_ticker(ticker, df, test_idx, rr, atr_mult, risk_per_trade,
                     equity_ref, max_hold, long_only, signal_fn):
    """Walk the test window for one ticker. Mutates equity_ref (a 1-element list)
    so position sizing compounds across the whole basket in date order."""
    trades = []
    pos = None  # dict: side, entry, stop, target, entry_date, held, risk_amt

    for i in test_idx:
        bar = df.iloc[i]
        d = df.index[i]

        if pos is not None:
            hit_stop = bar["Low"] <= pos["stop"] if pos["side"] == "long" else bar["High"] >= pos["stop"]
            hit_tgt = bar["High"] >= pos["target"] if pos["side"] == "long" else bar["Low"] <= pos["target"]
            exit_px = exit_reason = None
            if hit_stop:                       # stop checked first (pessimistic)
                exit_px, exit_reason = pos["stop"], "stop"
            elif hit_tgt:
                exit_px, exit_reason = pos["target"], "target"
            else:
                pos["held"] += 1
                flip = signal_fn(df.iloc[:i + 1], ticker, rr, atr_mult).action
                if (pos["side"] == "long" and flip == "SELL") or (pos["side"] == "short" and flip == "BUY"):
                    exit_px, exit_reason = float(bar["Close"]), "signal"
                elif pos["held"] >= max_hold:
                    exit_px, exit_reason = float(bar["Close"]), "time"

            if exit_px is not None:
                r = pos["risk_per_unit"]
                move = (exit_px - pos["entry"]) if pos["side"] == "long" else (pos["entry"] - exit_px)
                r_mult = move / r if r else 0.0
                pnl = r_mult * pos["risk_amt"]
                equity_ref[0] += pnl
                trades.append(Trade(
                    ticker, pos["side"], pos["entry_date"], round(pos["entry"], 2),
                    d.strftime("%Y-%m-%d"), round(exit_px, 2), round(r_mult, 2),
                    round(pnl, 2), exit_reason))
                pos = None
                continue  # one action per bar

        if pos is None:
            sig = signal_fn(df.iloc[:i + 1], ticker, rr, atr_mult)
            take = sig.action == "BUY" or (sig.action == "SELL" and not long_only)
            if take:
                side = "long" if sig.action == "BUY" else "short"
                risk_per_unit = abs(sig.price - sig.stop)
                if risk_per_unit <= 0:
                    continue
                pos = {
                    "side": side, "entry": sig.price, "stop": sig.stop,
                    "target": sig.target, "entry_date": d.strftime("%Y-%m-%d"),
                    "held": 0, "risk_per_unit": risk_per_unit,
                    "risk_amt": equity_ref[0] * risk_per_trade,
                }
    return trades


def _metrics(trades, equity: pd.Series, capital: float) -> dict:
    n = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_win = sum(t.pnl for t in wins)
    gross_loss = -sum(t.pnl for t in losses)
    roll_max = equity.cummax()
    dd = equity / roll_max - 1
    rets = equity.pct_change().dropna()
    sharpe = (rets.mean() / rets.std() * (252 ** 0.5)) if rets.std() else 0.0
    return {
        "trades": n,
        "win_rate": round(len(wins) / n, 3) if n else 0.0,
        "avg_R": round(sum(t.r_multiple for t in trades) / n, 2) if n else 0.0,
        "expectancy_$": round(sum(t.pnl for t in trades) / n, 2) if n else 0.0,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else float("inf"),
        "total_return": round(equity.iloc[-1] / capital - 1, 4),
        "final_equity": round(float(equity.iloc[-1]), 2),
        "max_drawdown": round(float(dd.min()), 4),
        "sharpe": round(float(sharpe), 2),
        "best_trade_$": round(max((t.pnl for t in trades), default=0.0), 2),
        "worst_trade_$": round(min((t.pnl for t in trades), default=0.0), 2),
    }


def run_backtest(tickers=None, months: int = 1, capital: float = 10_000,
                 risk_per_trade: float = config.RISK_PER_TRADE,
                 rr: float = config.RISK_REWARD, atr_mult: float = config.ATR_MULT,
                 long_only: bool = True, max_hold: int = 15,
                 out_dir: str = config.RESULTS_DIR, save: bool = True,
                 alpha: str = "momentum", signal_fn=None) -> BacktestResult:
    tickers = [t.upper() for t in (tickers or config.DEFAULT_TICKERS)]
    signal_fn = signal_fn or get_alpha(alpha)
    test_bars = max(5, months * TRADING_DAYS_PER_MONTH)
    # Pull plenty of warmup so the 50d average / 63d return are valid in the window.
    start = (date.today() - timedelta(days=months * 31 + 320)).isoformat()

    frames, test_dates = {}, set()
    for t in tickers:
        try:
            df = data.get_prices(t, start=start)
        except Exception as e:
            print(f"  skip {t}: {e}")
            continue
        if len(df) < test_bars + 70:
            print(f"  skip {t}: short history ({len(df)} bars)")
            continue
        frames[t] = df
        test_dates.update(df.index[-test_bars:])

    if not frames:
        raise RuntimeError("no usable tickers")

    timeline = sorted(test_dates)
    equity_ref = [capital]
    all_trades = []
    # Process tickers in turn; equity compounds across the basket.
    for t, df in frames.items():
        idx = [df.index.get_loc(d) for d in df.index[-test_bars:]]
        all_trades += _simulate_ticker(t, df, idx, rr, atr_mult, risk_per_trade,
                                       equity_ref, max_hold, long_only, signal_fn)

    all_trades.sort(key=lambda x: x.exit_date)
    equity = pd.Series(capital, index=pd.to_datetime(timeline), dtype="float64")
    running = capital
    for tr in all_trades:
        running += tr.pnl
        equity.loc[equity.index >= pd.to_datetime(tr.exit_date)] = running

    metrics = _metrics(all_trades, equity, capital)
    params = {"tickers": tickers, "months": months, "capital": capital,
              "risk_per_trade": risk_per_trade, "rr": rr, "atr_mult": atr_mult,
              "long_only": long_only, "max_hold": max_hold, "alpha": alpha}
    result = BacktestResult(all_trades, equity, metrics, params)
    if save:
        _save(result, out_dir)
    return result


def _save(result: BacktestResult, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    pd.DataFrame([asdict(t) for t in result.trades]).to_csv(
        os.path.join(out_dir, f"trades_{ts}.csv"), index=False)
    result.equity.rename("equity").to_csv(os.path.join(out_dir, f"equity_{ts}.csv"))
    with open(os.path.join(out_dir, f"summary_{ts}.json"), "w") as fh:
        json.dump({"metrics": result.metrics, "params": result.params}, fh, indent=2)

    eq = result.equity
    dd = eq / eq.cummax() - 1
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(eq.index, eq.values, color="#1f6feb", lw=1.6)
    ax1.set_title(f"Equity  |  return {result.metrics['total_return']*100:+.1f}%  "
                  f"max DD {result.metrics['max_drawdown']*100:.1f}%  "
                  f"win {result.metrics['win_rate']*100:.0f}%  "
                  f"({result.metrics['trades']} trades)")
    ax1.set_ylabel("Equity ($)")
    ax1.grid(alpha=0.3)
    ax2.fill_between(dd.index, dd.values * 100, 0, color="#d1242f", alpha=0.4)
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    png_path = os.path.join(out_dir, f"equity_{ts}.png")
    fig.savefig(png_path, dpi=120, facecolor="white")
    plt.close(fig)
    try:  # flatten RGBA -> RGB so every image viewer opens it cleanly
        from PIL import Image
        Image.open(png_path).convert("RGB").save(png_path)
    except Exception:
        pass
    print(f"  saved trades/equity/summary/png to {out_dir}/ (stamp {ts})")
