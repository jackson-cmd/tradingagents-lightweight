"""The agent: glue the pieces into one decision.

Pipeline per ticker:
    prices -> momentum signal (lead)
           -> news headlines -> fast long/short scan (confirm/veto)
           -> fundamentals (context)
           -> optional LLM for the final call and a one-line rationale
           -> BUY / SELL / HOLD with entry, stop and 1:2 target

With no API key it stops at the rule signal. That path is free, deterministic and
fast - the same path the backtest runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import config, data, llm, news
from . import prompts as P
from . import strategy
from .sentiment import quick_sentiment


@dataclass
class Decision:
    ticker: str
    action: str
    confidence: float
    price: float
    stop: float
    target: float
    rr: float
    momentum: float
    rationale: str
    source: str                 # "rule" or "llm"
    news_bias: float = 0.0
    headlines: list = field(default_factory=list)
    fundamentals: dict = field(default_factory=dict)

    def __str__(self) -> str:
        head = f"{self.action}  {self.ticker} @ {self.price:.2f}  ({self.source}, conf {self.confidence:.0%})"
        if self.action in ("BUY", "SELL"):
            risk = abs(self.price - self.stop)
            reward = abs(self.target - self.price)
            head += (f"\n  stop {self.stop:.2f}  target {self.target:.2f}  "
                     f"R/R 1:{(reward / risk):.1f}" if risk else "")
        return (f"{head}\n  momentum {self.momentum:+.0f}/6   news {self.news_bias:+.2f}"
                f"\n  {self.rationale}")


class Agent:
    def __init__(self, provider: str | None = None, model: str | None = None,
                 use_llm: bool = True, rr: float = config.RISK_REWARD,
                 atr_mult: float = config.ATR_MULT, alpha: str = "momentum",
                 signal_fn=None, news_source: str | None = None):
        self.provider = provider or config.LLM_PROVIDER
        self.model = model or config.LLM_MODEL
        self.use_llm = use_llm
        self.rr = rr
        self.atr_mult = atr_mult
        self.news_source = news_source or config.NEWS_SOURCE
        # Pick the alpha: an explicit function wins, else look it up by name.
        self.signal_fn = signal_fn or strategy.get_alpha(alpha)

    def analyze(self, ticker: str) -> Decision:
        ticker = ticker.upper().strip()
        df = data.get_prices(ticker, period=config.LIVE_PERIOD)
        sig = self.signal_fn(df, ticker, self.rr, self.atr_mult)

        fund = data.get_fundamentals(ticker)
        try:
            raw_news = news.get_news(self.news_source, limit=40, tickers=[ticker])
        except Exception:
            raw_news = data.get_market_news(limit=40)   # fall back to RSS if configured
        headlines = [h["title"] for h in raw_news]
        bias, relevant = quick_sentiment(headlines, ticker, fund.get("Company", ""))
        shown = relevant or headlines[:6]

        # Rule decision first - it is always the fallback.
        decision = Decision(
            ticker=ticker, action=sig.action, confidence=_rule_conf(sig.momentum),
            price=sig.price, stop=sig.stop, target=sig.target, rr=self.rr,
            momentum=sig.momentum, rationale="; ".join(sig.reasons),
            source="rule", news_bias=bias, headlines=shown, fundamentals=fund,
        )

        if self.use_llm and llm.available(self.provider):
            try:
                reply = llm.chat(
                    P.SYSTEM,
                    P.build_user_prompt(ticker, sig, bias, shown, fund),
                    model=self.model, provider=self.provider,
                )
                parsed = llm.parse_decision(reply)
                if parsed:
                    action = parsed["action"]
                    stop, target = strategy._levels(
                        sig.price, sig.features.get("atr", 0.0),
                        action, self.rr, self.atr_mult)
                    decision.action = action
                    decision.stop, decision.target = stop, target
                    decision.confidence = parsed["confidence"]
                    decision.rationale = parsed["reason"] or decision.rationale
                    decision.source = "llm"
            except Exception as e:
                decision.rationale += f"  (llm skipped: {e})"

        return decision


def _rule_conf(score: float) -> float:
    # Map the -6..+6 score onto a rough 0.5..0.95 confidence band.
    return round(min(0.95, 0.5 + abs(score) / 12), 2)
