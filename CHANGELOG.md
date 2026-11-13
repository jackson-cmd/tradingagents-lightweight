# Changelog

Newest first. 中文版：[CHANGELOG_zh.md](CHANGELOG_zh.md)

## 0.1.0 (2026-11-13)

The first release on PyPI and as a Docker image.

- **Install with one command:** `pip install tradingagents-lightweight` (or `pipx install`), then run `talite`. Without installing anything, `uvx tradingagents-lightweight screen` runs it in a throwaway environment, and the image is `ghcr.io/jackson-cmd/tradingagents-lightweight`.
- **Momentum screen:** `talite screen` picks names in a confirmed uptrend from Finviz; `--backtest` backtests the picks and `--execute` paper-trades the BUYs.
- **One ticker end to end:** `talite analyze NVDA` scores the trend, reads the news (SEC 8-K filings by default, Benzinga or any RSS feed with `--news`) and returns BUY, SELL or HOLD with an entry, a 2×ATR stop and a 1:2 target. It is free without API keys; OpenAI, Anthropic, DeepSeek or Gemini can add an LLM layer (`pip install "tradingagents-lightweight[llm]"`).
- **Backtester:** `talite backtest` runs the same signal code over recent months, with a time stop.
- **Orders:** sized from the risk per trade, then logged to `results/paper_orders.csv` by the paper broker, or sent to Alpaca as a bracket order (paper account unless you ask for live).
- `talite --version` prints the version.
