# 更新记录

最新的在最上面。English: [CHANGELOG.md](CHANGELOG.md)

## 0.1.0（2026-11-13）

第一次发布到 PyPI，同时提供 Docker 镜像。

- **一条命令安装：** `pip install tradingagents-lightweight`（或者 `pipx install`），然后运行 `talite`。什么都不想装的话，`uvx tradingagents-lightweight screen` 会在临时环境里直接跑；Docker 镜像是 `ghcr.io/jackson-cmd/tradingagents-lightweight`。
- **动量选股：** `talite screen` 从 Finviz 挑出处在确认上升趋势里的股票；加 `--backtest` 回测这些股票，加 `--execute` 把 BUY 信号下成模拟单。
- **单只股票从头到尾：** `talite analyze NVDA` 给趋势打分、看新闻（默认 SEC 8-K 公告，用 `--news` 可以换成 Benzinga 或任意 RSS），给出 BUY、SELL 或 HOLD，附入场价、2 倍 ATR 止损和 1:2 目标价。不填 API key 也能免费跑；想加 LLM 层可以接 OpenAI、Anthropic、DeepSeek 或 Gemini（`pip install "tradingagents-lightweight[llm]"`）。
- **回测：** `talite backtest` 用同一套信号代码回测最近几个月，带时间止损。
- **下单：** 按每笔风险算仓位，模拟券商把订单记进 `results/paper_orders.csv`，也可以发到 Alpaca 下括号单（默认模拟盘，明确要求才走实盘）。
- `talite --version` 输出版本号。
