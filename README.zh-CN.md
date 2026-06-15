# TradingAgents-Lightweight（轻量版）

一个快速、便宜、以动量为先的摆动交易 agent。它自动筛动量股，用透明的规则引擎打分，
再结合新闻和基本面，给出带入场价、ATR 止损和固定 1:2 目标的 BUY/SELL/HOLD。
LLM 层是可选的——没有任何 API key 也能免费跑。

[English](README.md) | 中文

整条链路——数据、选股、打分、仓位——就是几百行你能读懂、也能 fork 改造的 Python。

## 它做什么

- **自己筛候选。** 用 Finviz 自动筛出处于确认上升趋势的名字，不用你一个个手敲 ticker。
- **一遍出结论。** 技术面主导，新闻快速判多空，瞄一眼基本面，一个结论——几秒，不是几分钟。
- **带计划下手。** 每个 BUY/SELL 都自带入场价、2×ATR 止损、固定 1:2 目标。
- **可插拔新闻。** 默认 SEC EDGAR 8-K（免费、无 key）；一个参数切到 Benzinga（付费）或任意 RSS。
- **任意模型，或不用模型。** OpenAI、Claude、DeepSeek、Gemini 随便接；没 key 就跑纯规则，免费。
- **诚实回测。** 实盘和回测跑同一套信号代码；资金曲线和回撤存本地。
- **算仓位并下单。** 基于风险的仓位计算；默认模拟盘，实盘走 Alpaca bracket。
- **接你自己的 alpha。** 策略就是注册表后的一个函数——注册、用 `--alpha` 选上即可。

## 目录

- [为什么要轻量版](#为什么要轻量版)
- [流程](#流程)
- [它怎么决定](#它怎么决定)
- [安装](#安装)
- [Docker](#docker)
- [自动选股](#自动选股)
- [回测](#回测)
- [接入你自己的-alpha](#接入你自己的-alpha)
- [下单](#下单)
- [选择模型](#选择模型)
- [数据来源](#数据来源)
- [配置](#配置)
- [券商](#券商)
- [路线图](#路线图)
- [免责声明](#免责声明)

## 为什么要轻量版

那种完整多 agent 的方案（多头研究员、空头研究员、风控、来回辩论）拿来**研究**一笔交易
怎么被论证出来挺好，但拿来交易又慢又烧 token。这里拿辩论换速度：一遍过，一个结论，两三秒，
便宜到开盘前能把整个自选股扫一遍。它先看价格行为，再扫一眼新闻定多空，然后直接下结论。
想要基本面深挖，这个不合适；想要一个马上能动手、有纪律的摆动信号，那就对了。

## 流程

```
  Finviz 选股器 ──→ 动量龙头（自动选）   ┐
                                          ├─→  ticker(s)
  或者你自己传 ticker ─────────────────── ┘        │
                                                   ▼
                                yfinance ──→ 日线 OHLCV
                                                   ▼
                    动量引擎 = 你的 ALPHA ──→ 打分 · ATR 止损 · 1:2 目标   ← 可换成你自己的
                                                   ▼
                    新闻 ──→ 快速多空扫描   （SEC · Benzinga · RSS）
                                                   ▼
                    Finviz ──→ 基本面：行业、市盈率、市值   （背景）
                                                   ▼
                    LLM（可选） ──→ 最终结论 + 一句理由
                                                   ▼
                    BUY / SELL / HOLD  +  入场 · 止损 · 目标（1:2）
                                                   ▼
                    仓位计算（风险预算） ──→ 券商（模拟 / Alpaca）
```

把 LLM 去掉，你照样拿到一个完整、确定的结论。

## 它怎么决定

- **顺势而为。** 六项检查——价格 vs 20 日线、20 vs 50 日线、近 1/3 月涨幅、MACD 柱、
  20 日变动率——每项投 +1 或 -1。得分 ≥ +3 是 **BUY**，≤ -3 是 **SELL**，中间是 **HOLD**。
- **让利润奔跑，把亏损砍掉。** 不抄底；RSI 冲过头（> 82）禁止新开多，免得买在插针最后一跳。
- **新闻只是加减分，不是论据。** 头条做关键词多空判断，影响信心，但不发起交易。
- **先定风险，再谈回报。** 止损放 2×ATR，目标是止损距离的两倍，永远 1:2。数学不成立就是 HOLD。
- **摆动周期。** 日线，持仓几天到一两周，带时间止损，不让死钱占着。

## 安装

```bash
git clone https://github.com/jackson-cmd/tradingagents-lightweight.git
cd tradingagents-lightweight

python -m venv .venv
source .venv/bin/activate      # Windows：.venv\Scripts\activate

pip install -r requirements.txt   # 或者：pip install -e .  （多出 `talite` 命令）
```

Python 3.9+。开箱即用，不需要任何 key——纯规则免费跑。

```bash
python -m talite screen                 # 自动选动量票
python -m talite analyze NVDA --no-llm  # 单票，免费
python -m talite backtest               # 回测默认篮子
```

跑了 `pip install -e .` 后可以省掉 `python -m`，直接 `talite screen` 等。

## Docker

```bash
docker build -t talite .
docker run --rm talite screen
docker run --rm -e OPENAI_API_KEY=$OPENAI_API_KEY talite analyze NVDA
docker run --rm -v "$PWD/results:/app/results" talite backtest
```

用 `-e` 传 key，或者 `--env-file .env` 挂一个环境文件。

## 自动选股

```bash
talite screen                    # 当前的动量龙头
talite screen --top 20           # 撒大网
talite screen --backtest         # 选完顺手回测
talite screen --top 5 --execute  # 选股 + 分析 + 给 BUY 挂模拟单
```

默认筛选只留流动性好、非仙股、且处于确认上升趋势（站上 20/50 日线、季度上涨）的名字，
再按周/月/季强度加权排序。筛选条件、权重都在 [`talite/screener.py`](talite/screener.py) 里调。

## 回测

回测器跑的是和实盘一样的信号代码，把资金曲线、回撤和成交记录存到 `results/`。

```bash
talite backtest                          # 默认大盘股篮子，过去一个月
talite backtest NVDA AMD HPE --months 3  # 你的篮子，三个月
talite screen --backtest                 # 回测选股器当前的票
```

怎么保证干净：第 *i* 根 K 线的信号只看到第 *i* 根及之前，持仓从下一根开始管理，
止损和目标落同一根时假设先打止损。固定比例仓位，所以赢一笔 +2R，被止损 -1R。

> 选股器那一档回测天然是事后诸葛——这些名字之所以被筛出来，就是因为它们**已经**涨过了，
> 拿它们涨的那个月去回测，结果会被美化。它只能用来验证闭环跑通；信任任何数字之前，
> 先用模拟盘往前跑一段。

## 接入你自己的 alpha

策略就是注册表后面的一个函数。写好、注册、选上——它跑实盘和回测的方式跟内置的一模一样。

```python
from talite.strategy import register_alpha, Signal
from talite import run_backtest

@register_alpha("gap_and_go")
def my_alpha(df, ticker="", rr=2.0, atr_mult=2.0) -> Signal:
    close = float(df["Close"].iloc[-1])
    # ... 你的 edge 写这儿 ...
    return Signal(ticker, "BUY", close, stop=close * 0.95,
                  target=close * 1.10, rr=rr, momentum=0,
                  reasons=["放量跳空"])

run_backtest(["NVDA", "AMD"], months=1, alpha="gap_and_go")
```

```bash
talite analyze NVDA --alpha gap_and_go
talite backtest NVDA AMD --alpha gap_and_go
```

动量引擎是默认 alpha（`"momentum"`），你的就放它旁边——同样的止损、1:2、回测器和下单。

## 下单

它会把仓位算到"被止损正好亏掉你的风险预算"（默认本金的 1%），然后发单。

```bash
talite analyze HPE --execute                  # 模拟单，记到 results/
talite screen --top 5 --execute               # 自动选股 + 给 BUY 挂模拟单
talite analyze HPE --execute --broker alpaca  # 走 Alpaca 的 bracket 单（模拟）
talite analyze HPE --execute --broker alpaca --live   # ...来真的
```

默认模拟盘，写到 `results/paper_orders.csv`，啥都不出本机。Alpaca 适配器一次性挂 bracket
（入场 + 1:2 止盈 + 止损），默认走模拟端点；只有 `--live` 才真正激活实盘。
仓位逻辑在 [`talite/execution.py`](talite/execution.py)。

## 选择模型

与厂商无关，provider 按模型名自动推断，也能手动指定。

```bash
talite analyze TSLA --model gpt-4.1-mini       # OpenAI
talite analyze TSLA --model claude-sonnet-4-6  # Anthropic
talite analyze TSLA --model deepseek-chat      # DeepSeek
talite analyze TSLA --model gemini-2.0-flash   # Gemini
```

`gpt-4.1-mini`（或 `-nano`）是便宜的默认：进去一份短 prompt，出来一行 JSON 结论。
LLM 是可选的——`--no-llm` 只跑规则，免费且确定。edge 在规则里，LLM 只是微调最终结论。

## 数据来源

| 层 | 来源 | 说明 |
|------|--------|------|
| 行情 | [yfinance](https://github.com/ranaroussi/yfinance) | 日线 OHLCV，免费 |
| 选股 + 基本面 | [Finviz](https://finviz.com/)（经 [finvizfinance](https://github.com/lit26/finvizfinance)） | 动量筛选、行业、市盈率、市值 |
| 新闻（免费，默认） | [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | 最新 8-K 文件 —— `NEWS_SOURCE=sec` |
| 新闻（付费） | [Benzinga](https://www.benzinga.com/apis/) | 实时、按个股 —— `NEWS_SOURCE=benzinga` |
| 新闻（RSS） | 任意源 | 设 `RSS_FEED_URL`、`NEWS_SOURCE=rss` |

新闻层抽风时，agent 会退回到只凭价格行为，继续跑。

## 配置

把 `.env.example` 复制成 `.env`，只填你用的：

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

# 只有接实盘才需要：
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
```

## 券商

模拟盘开箱即用。要真成交：

- **Alpaca** —— [免佣 API](https://alpaca.markets/)，带模拟沙箱，用
  [`alpaca-py`](https://github.com/alpacahq/alpaca-py)。已经接好（`--broker alpaca`）。
- **盈透 Interactive Brokers** —— [TWS / Client Portal API](https://www.interactivebrokers.com/en/trading/ib-api.php)，
  最省心用 [`ib_async`](https://github.com/ib-api-reloaded/ib_async)。
- **tastytrade** —— [开发者 API](https://developer.tastytrade.com/) 和官方
  [Python SDK](https://github.com/tastyware/tastytrade)。

> 先模拟盘，永远先模拟盘。

## 路线图

- [x] 自动选股（Finviz 动量）
- [x] 可插拔的 alpha 注册表
- [x] 可插拔新闻源（SEC / Benzinga / RSS）
- [x] 仓位计算 + 模拟 / Alpaca 下单
- [x] Docker 镜像
- [ ] 更多券商适配（IBKR、tastytrade）
- [ ] 可选日内周期，做更快的摆动
- [ ] 组合层面仓位管理和敞口上限

## 免责声明

研究与学习用的软件，不构成投资建议。趋势策略在震荡和反转里会亏，回测代表不了未来
（尤其是上面那种 in-sample 的），你是会亏钱的。盈亏自负，下真金白银前先用模拟盘跑。

## 许可

MIT —— 见 [LICENSE](LICENSE)。
