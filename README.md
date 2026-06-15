# TradingAgents-Lightweight

A fast, cheap, momentum-first swing-trading agent. It screens for momentum
stocks, scores them with a transparent rule engine, checks news and
fundamentals, and returns a BUY/SELL/HOLD with an entry, an ATR stop, and a
fixed 1:2 target. The LLM layer is optional — it runs free with no API keys.

English | [中文](README.zh-CN.md)

The whole chain — data, screening, scoring, position sizing — is a few hundred
lines of readable Python you can fork and adapt.

## What it does

- **Screens its own candidates.** Auto-screens Finviz for names in a confirmed
  uptrend, instead of you typing tickers.
- **Decides in one pass.** Momentum-led technicals, a quick news long/short read,
  a glance at fundamentals, one call — seconds, not minutes.
- **Trades with a plan.** Every BUY/SELL ships with an entry, a 2×ATR stop, and a
  fixed 1:2 target.
- **Pluggable news.** SEC EDGAR 8-K filings by default (free, no key); Benzinga
  (paid) or any RSS feed with one flag.
- **Any model, or none.** OpenAI, Claude, DeepSeek, Gemini all plug in. No key? It
  runs the rule engine for free.
- **Honest backtester.** The same signal code runs live and in the backtest;
  equity curve and drawdown saved locally.
- **Sizes and places the order.** Risk-based position sizing; paper by default,
  Alpaca bracket orders for real.
- **Bring your own alpha.** The strategy is one function behind a registry —
  register yours and select it with `--alpha`.

## Contents

- [Why lightweight](#why-lightweight)
- [Pipeline](#pipeline)
- [How it decides](#how-it-decides)
- [Install](#install)
- [Docker](#docker)
- [Auto stock picking](#auto-stock-picking)
- [Backtest](#backtest)
- [Add your own alpha](#add-your-own-alpha)
- [Place the order](#place-the-order)
- [Choose your model](#choose-your-model)
- [Data sources](#data-sources)
- [Configuration](#configuration)
- [Brokers](#brokers)
- [Roadmap](#roadmap)
- [Disclaimer](#disclaimer)

## Why lightweight

Full multi-agent setups (a bull researcher, a bear researcher, a risk manager,
debate rounds) are great for *studying* how a decision gets argued out, but slow
and token-heavy for actually trading. This trades the debate for speed: one
pass, one decision, a couple of seconds, cheap enough to scan a whole watchlist
before the open. It reads price action first, checks headlines for a long/short
lean, and commits. If you want a fundamentals deep-dive, this isn't it; if you
want a disciplined swing signal you can act on now, that's the idea.

## Pipeline

```
  Finviz screener ──→ momentum leaders (auto-pick)   ┐
                                                      ├─→  ticker(s)
  or pass your own tickers ───────────────────────── ┘        │
                                                               ▼
                                          yfinance ──→ daily OHLCV
                                                               ▼
                          momentum engine = the ALPHA ──→ score · ATR stop · 1:2 target   ← swap your own
                                                               ▼
                          news ──→ fast long/short scan   (SEC · Benzinga · RSS)
                                                               ▼
                          Finviz ──→ fundamentals: sector, P/E, market cap   (context)
                                                               ▼
                          LLM (optional) ──→ final call + one-line reason
                                                               ▼
                          BUY / SELL / HOLD  +  entry · stop · target (1:2)
                                                               ▼
                          position sizing (risk budget) ──→ broker (paper / Alpaca)
```

Drop the LLM and you still get a complete, deterministic decision.

## How it decides

- **Trade with the trend.** Six checks — price vs the 20-day, 20- vs 50-day, 1-
  and 3-month return, MACD histogram, 20-day rate of change — each votes +1 or
  -1. Score ≥ +3 is a **BUY**, ≤ -3 is a **SELL**, in between is **HOLD**.
- **Ride winners, cut losers.** No bottom-fishing; an overheated RSI (> 82)
  blocks new longs so you're not buying the last tick of a spike.
- **News is a tiebreaker, not the thesis.** Headlines get a quick keyword lean;
  it nudges conviction, it doesn't start trades.
- **Risk fixed before reward.** Stop at 2×ATR, target at twice the stop distance
  — 1:2, always. If the math doesn't fit, it's a HOLD.
- **Swing timeframe.** Daily bars, holds of days to a couple of weeks, with a
  time stop so dead money doesn't sit.

## Install

```bash
git clone https://github.com/jackson-cmd/tradingagents-lightweight.git
cd tradingagents-lightweight

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt   # or: pip install -e .  (adds the `talite` command)
```

Python 3.9+. No API key needed to start — it runs the rules for free.

```bash
python -m talite screen                 # auto-pick momentum names
python -m talite analyze NVDA --no-llm  # one ticker, free
python -m talite backtest               # backtest the default basket
```

With `pip install -e .` you can drop `python -m` and just run `talite screen`, etc.

## Docker

```bash
docker build -t talite .
docker run --rm talite screen
docker run --rm -e OPENAI_API_KEY=$OPENAI_API_KEY talite analyze NVDA
docker run --rm -v "$PWD/results:/app/results" talite backtest
```

Pass keys with `-e`, or mount an env file with `--env-file .env`.

## Auto stock picking

```bash
talite screen                    # top momentum names right now
talite screen --top 20           # cast a wider net
talite screen --backtest         # screen, then backtest the picks
talite screen --top 5 --execute  # screen, analyze, paper-trade the BUYs
```

The default filters keep it to liquid, non-penny names in a confirmed uptrend
(above the 20- and 50-day, up on the quarter), then rank by a blend of
weekly/monthly/quarterly strength. Tune the filters and weights in
[`talite/screener.py`](talite/screener.py).

## Backtest

The backtester runs the same signal code as live trading and saves an equity
curve, drawdown and trade log to `results/`.

```bash
talite backtest                          # default mega-cap basket, last month
talite backtest NVDA AMD HPE --months 3  # your basket, 3 months
talite screen --backtest                 # backtest the current screener picks
```

How it stays clean: signals on bar *i* only see data through bar *i*, positions
are managed from the next bar, and a stop and target in the same bar assume the
stop hit first. Sizing is fixed-fractional, so a winner is +2R and a stop-out is
-1R.

> A screener-picks backtest is hindsight by construction — those names are
> flagged *because* they already trended, so backtesting the month they ran
> flatters the result. Use it to check the loop works end to end, then
> paper-trade forward before trusting any number.

## Add your own alpha

The strategy is one function behind a registry. Register it, select it — it
trades and backtests exactly like the built-in one.

```python
from talite.strategy import register_alpha, Signal
from talite import run_backtest

@register_alpha("gap_and_go")
def my_alpha(df, ticker="", rr=2.0, atr_mult=2.0) -> Signal:
    close = float(df["Close"].iloc[-1])
    # ... your edge here ...
    return Signal(ticker, "BUY", close, stop=close * 0.95,
                  target=close * 1.10, rr=rr, momentum=0,
                  reasons=["gap up on volume"])

run_backtest(["NVDA", "AMD"], months=1, alpha="gap_and_go")
```

```bash
talite analyze NVDA --alpha gap_and_go
talite backtest NVDA AMD --alpha gap_and_go
```

The momentum engine ships as the default alpha (`"momentum"`); yours sits right
next to it — same stops, same 1:2, same backtester, same execution.

## Place the order

It sizes the position so a stop-out costs exactly your risk budget (1% of equity
by default), then routes it.

```bash
talite analyze HPE --execute                  # paper order, logged to results/
talite screen --top 5 --execute               # auto-pick + paper-trade the BUYs
talite analyze HPE --execute --broker alpaca  # bracket order via Alpaca (paper)
talite analyze HPE --execute --broker alpaca --live   # ...for real
```

Paper is the default and writes to `results/paper_orders.csv` — nothing leaves
your machine. The Alpaca adapter places a one-shot bracket (entry + 1:2
take-profit + stop-loss) and defaults to the paper endpoint; `--live` is the only
thing that arms it. Sizing lives in [`talite/execution.py`](talite/execution.py).

## Choose your model

Provider-agnostic; inferred from the model name or set explicitly.

```bash
talite analyze TSLA --model gpt-4.1-mini       # OpenAI
talite analyze TSLA --model claude-sonnet-4-6  # Anthropic
talite analyze TSLA --model deepseek-chat      # DeepSeek
talite analyze TSLA --model gemini-2.0-flash   # Gemini
```

`gpt-4.1-mini` (or `-nano`) is a cheap default: a short prompt in, a one-line
JSON verdict out. The LLM is optional — `--no-llm` runs the rules alone, free and
deterministic. The edge is in the rules; the LLM just refines the final call.

## Data sources

| Layer | Source | Notes |
|------|--------|------|
| Prices | [yfinance](https://github.com/ranaroussi/yfinance) | daily OHLCV, free |
| Screening + fundamentals | [Finviz](https://finviz.com/) via [finvizfinance](https://github.com/lit26/finvizfinance) | momentum screen, sector, P/E, market cap |
| News (free, default) | [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | latest 8-K filings — `NEWS_SOURCE=sec` |
| News (paid) | [Benzinga](https://www.benzinga.com/apis/) | real-time, per-ticker — `NEWS_SOURCE=benzinga` |
| News (RSS) | any feed | set `RSS_FEED_URL`, `NEWS_SOURCE=rss` |

If the news layer is down, the agent falls back to price action alone and keeps
going.

## Configuration

Copy `.env.example` to `.env` and set only what you use:

```ini
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=sk-...

NEWS_SOURCE=sec               # sec | benzinga | rss
BENZINGA_API_KEY=
SEC_USER_AGENT=tradingagents-lightweight you@example.com

RISK_REWARD=2.0
ATR_MULT=2.0
RISK_PER_TRADE=0.01

# Only if you wire live execution:
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
```

## Brokers

Paper trading works out of the box. For real fills:

- **Alpaca** — [commission-free API](https://alpaca.markets/) with a paper
  sandbox, via [`alpaca-py`](https://github.com/alpacahq/alpaca-py). Wired up
  already (`--broker alpaca`).
- **Interactive Brokers** — [TWS / Client Portal API](https://www.interactivebrokers.com/en/trading/ib-api.php),
  e.g. via [`ib_async`](https://github.com/ib-api-reloaded/ib_async).
- **tastytrade** — [developer API](https://developer.tastytrade.com/) and the
  official [Python SDK](https://github.com/tastyware/tastytrade).

> Paper-trade first. Always.

## Roadmap

- [x] Auto stock screening (Finviz momentum)
- [x] Pluggable alpha registry
- [x] Pluggable news sources (SEC / Benzinga / RSS)
- [x] Position sizing + paper / Alpaca execution
- [x] Docker image
- [ ] More broker adapters (IBKR, tastytrade)
- [ ] Optional intraday timeframe for faster swings
- [ ] Portfolio-level sizing and exposure caps

## Disclaimer

Software for research and education, not financial advice. Momentum strategies
lose in chop and reversals, backtests are not the future (especially in-sample
ones), and you can lose money. Trade your own account at your own risk.
Paper-trade before you risk a cent.

## License

MIT — see [LICENSE](LICENSE).
