"""Provider-agnostic chat. Bring whatever model you like.

OpenAI, DeepSeek and Gemini all speak the OpenAI Chat Completions format, so they
share one code path with different base URLs. Anthropic uses its own SDK. If no
key is set for the chosen provider the caller falls back to the rule engine, so a
key is never strictly required.
"""
from __future__ import annotations

import json
import os

# Provider -> OpenAI-compatible base URL (None means native OpenAI endpoint).
BASE_URL = {
    "openai": None,
    "deepseek": "https://api.deepseek.com",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}

KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def infer_provider(model: str) -> str:
    m = (model or "").lower()
    if "claude" in m:
        return "anthropic"
    if "deepseek" in m:
        return "deepseek"
    if "gemini" in m:
        return "gemini"
    return "openai"  # gpt-*, o*, and anything else default here


def available(provider: str) -> bool:
    return bool(os.getenv(KEY_ENV.get(provider, "")))


def chat(system: str, user: str, model: str = "gpt-4.1-mini",
         provider: str | None = None, temperature: float = 0.2,
         max_tokens: int = 300) -> str:
    provider = provider or infer_provider(model)
    key = os.getenv(KEY_ENV[provider])
    if not key:
        raise RuntimeError(f"{KEY_ENV[provider]} is not set")

    if provider == "anthropic":
        from anthropic import Anthropic
        resp = Anthropic(api_key=key).messages.create(
            model=model, system=system, max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text

    from openai import OpenAI
    base = BASE_URL.get(provider)
    client = OpenAI(api_key=key, base_url=base) if base else OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=model, temperature=temperature, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content


def parse_decision(text: str) -> dict | None:
    """Pull the {action, confidence, reason} JSON out of a model reply."""
    if not text:
        return None
    s = text.strip()
    if "```" in s:                       # strip code fences if present
        s = s.split("```")[1].lstrip("json").strip() if s.count("```") >= 2 else s
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        d = json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        return None
    action = str(d.get("action", "")).upper()
    if action not in ("BUY", "SELL", "HOLD"):
        return None
    return {
        "action": action,
        "confidence": float(d.get("confidence", 0.5) or 0.5),
        "reason": str(d.get("reason", "")).strip(),
    }
