"""Analyze a single ticker. Runs from the repo without installing.

    python examples/run_analyze.py NVDA
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from talite import Agent

ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
use_llm = "--llm" in sys.argv  # off by default so it runs with no API key
print(Agent(use_llm=use_llm).analyze(ticker))
