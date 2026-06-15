"""Prompts. Kept short on purpose - short prompts are cheaper and faster, and a
swing call does not need an essay to justify it.
"""

SYSTEM = (
    "You are a disciplined swing trader. You get a technical snapshot and a few "
    "market headlines and you commit to one call.\n"
    "Rules:\n"
    "- Momentum leads. Trade with the trend: ride strength, cut weakness.\n"
    "- News only confirms or vetoes the technical read. Never chase a single headline.\n"
    "- Risk/reward is fixed at 1:2. Do not widen a stop to justify a trade.\n"
    "- Mixed picture means HOLD. Sitting out is a position.\n"
    'Reply with JSON only: {"action":"BUY|SELL|HOLD","confidence":0-1,'
    '"reason":"one short sentence"}'
)


def build_user_prompt(ticker, sig, news_bias, headlines, fund) -> str:
    f = sig.features
    cap = fund.get("Market Cap", "?")
    pe = fund.get("P/E", "?")
    sector = fund.get("Sector", "?")
    lines = [
        f"Ticker: {ticker}",
        f"Price: {sig.price:.2f}  RSI: {f.get('rsi', float('nan')):.0f}  "
        f"MACD hist: {f.get('macd_hist', 0):+.2f}",
        f"vs 20d: {'above' if f.get('close',0) > f.get('sma20',0) else 'below'}  "
        f"trend: {'up' if f.get('sma20',0) > f.get('sma50',0) else 'down'}",
        f"Return 1m: {f.get('ret_1m',0)*100:+.1f}%  3m: {f.get('ret_3m',0)*100:+.1f}%",
        f"Momentum score: {sig.momentum:+.0f}/6   Rule signal: {sig.action}",
        f"Fundamentals: sector {sector}, P/E {pe}, mkt cap {cap}",
        f"News tone (rule scan): {news_bias:+.2f} on -1..+1",
    ]
    if headlines:
        lines.append("Headlines:")
        lines += [f"- {h}" for h in headlines[:6]]
    lines.append('Decide. JSON only.')
    return "\n".join(lines)
