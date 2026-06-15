"""Command line.

    talite screen                       # auto-pick momentum names from Finviz
    talite screen --backtest            # ...and backtest the picks
    talite screen --top 5 --execute     # ...and paper-trade the BUYs (full auto)
    talite analyze NVDA                  # one ticker, end to end
    talite analyze NVDA --execute        # ...and place the (paper) order
    talite backtest AAPL MSFT NVDA      # backtest a basket over the last month
"""
from __future__ import annotations

import argparse

from . import config


def _route_order(decision, args):
    """Size the decision into an order and submit it to the chosen broker."""
    from .execution import get_broker, order_from_decision
    order = order_from_decision(decision, equity=args.equity, risk_per_trade=args.risk)
    if not order:
        print(f"  {decision.ticker}: {decision.action} - no order")
        return
    broker = get_broker(args.broker, live=args.live, out_dir=args.out)
    res = broker.submit(order)
    print(f"  {order.ticker}: {order.side.upper()} {order.qty} @ {order.entry} "
          f"stop {order.stop} target {order.target}  ->  {broker.name}: {res['status']}")


def _analyze(args):
    from .agent import Agent
    agent = Agent(provider=args.provider, model=args.model,
                  use_llm=not args.no_llm, alpha=args.alpha, news_source=args.news)
    decision = agent.analyze(args.ticker)
    print(decision)
    if args.execute:
        print("\nexecution:")
        _route_order(decision, args)


def _backtest(args):
    from .backtest import run_backtest
    res = run_backtest(
        tickers=args.tickers or None, months=args.months, capital=args.capital,
        risk_per_trade=args.risk, rr=args.rr, atr_mult=args.atr_mult,
        long_only=not args.shorts, max_hold=args.max_hold, out_dir=args.out,
        alpha=args.alpha)
    _print_backtest(res, args)


def _screen(args):
    from .screener import screen_momentum
    from .screener import format_table
    df = screen_momentum(top_n=args.top, include_overheated=args.include_overheated)
    print("Momentum leaders (Finviz auto-screen):")
    print(format_table(df))
    tickers = df["Ticker"].tolist() if not df.empty else []
    if not tickers:
        return

    if args.backtest:
        from .backtest import run_backtest
        res = run_backtest(tickers, months=args.months, capital=args.capital,
                           risk_per_trade=args.risk, rr=args.rr,
                           atr_mult=args.atr_mult, out_dir=args.out, alpha=args.alpha)
        _print_backtest(res, args)

    if args.execute:
        from .agent import Agent
        agent = Agent(use_llm=not args.no_llm, alpha=args.alpha, news_source=args.news)
        print(f"\nrouting BUY signals to {args.broker}:")
        for t in tickers:
            try:
                decision = agent.analyze(t)
            except Exception as e:
                print(f"  {t}: skip ({e})")
                continue
            if decision.action == "BUY":
                _route_order(decision, args)
            else:
                print(f"  {t}: {decision.action} (skip)")


def _print_backtest(res, args):
    print(f"\n=== backtest: last {args.months} month(s), alpha '{res.params['alpha']}', "
          f"1:{args.rr:.0f} R/R ===")
    print(f"tickers: {', '.join(res.params['tickers'])}")
    for k, v in res.metrics.items():
        print(f"{k:14}: {v}")
    if res.trades:
        print("\nlast trades:")
        for t in res.trades[-8:]:
            print(f"  {t.exit_date}  {t.ticker:5} {t.side:5} "
                  f"{t.r_multiple:+.2f}R  ${t.pnl:+.2f}  ({t.exit_reason})")


def _add_common(p):
    p.add_argument("--alpha", default="momentum", help="registered alpha to use")
    p.add_argument("--news", default=None, help="news source: sec | benzinga | rss")
    p.add_argument("--rr", type=float, default=config.RISK_REWARD)
    p.add_argument("--atr-mult", type=float, default=config.ATR_MULT)
    p.add_argument("--risk", type=float, default=config.RISK_PER_TRADE,
                   help="fraction of equity risked per trade")
    p.add_argument("--out", default=config.RESULTS_DIR)


def _add_exec(p):
    p.add_argument("--execute", action="store_true", help="place orders for BUY/SELL")
    p.add_argument("--broker", default="paper", help="paper | alpaca")
    p.add_argument("--live", action="store_true", help="alpaca: use live, not paper")
    p.add_argument("--equity", type=float, default=10_000, help="account size for sizing")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="talite",
        description="TradingAgents-Lightweight: momentum-first swing signals.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("screen", help="auto-pick momentum names from Finviz")
    s.add_argument("--top", type=int, default=15)
    s.add_argument("--include-overheated", action="store_true",
                   help="keep names already up >25%% on the week")
    s.add_argument("--backtest", action="store_true", help="backtest the picks")
    s.add_argument("--months", type=int, default=1)
    s.add_argument("--capital", type=float, default=10_000)
    s.add_argument("--no-llm", action="store_true")
    _add_common(s)
    _add_exec(s)
    s.set_defaults(func=_screen)

    a = sub.add_parser("analyze", help="analyze one ticker now")
    a.add_argument("ticker")
    a.add_argument("--provider", default=None, help="openai|anthropic|deepseek|gemini")
    a.add_argument("--model", default=None, help="e.g. gpt-4.1-mini")
    a.add_argument("--no-llm", action="store_true", help="rule engine only, no API call")
    _add_common(a)
    _add_exec(a)
    a.set_defaults(func=_analyze)

    b = sub.add_parser("backtest", help="backtest a basket over recent months")
    b.add_argument("tickers", nargs="*", help=f"default: {' '.join(config.DEFAULT_TICKERS)}")
    b.add_argument("--months", type=int, default=1)
    b.add_argument("--capital", type=float, default=10_000)
    b.add_argument("--max-hold", type=int, default=15, help="time stop in bars")
    b.add_argument("--shorts", action="store_true", help="allow short trades too")
    _add_common(b)
    b.set_defaults(func=_backtest)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
