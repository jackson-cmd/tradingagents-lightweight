"""The command line parses what the README shows, and `--version` answers without touching the network."""

import pytest

from talite import __version__
from talite.cli import build_parser, main


def test_version_prints_the_package_version(capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--version"])
    assert stop.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_every_command_parses():
    parser = build_parser()
    assert parser.parse_args(["screen", "--top", "5", "--backtest"]).top == 5
    analyze = parser.parse_args(["analyze", "NVDA", "--no-llm", "--execute"])
    assert (analyze.ticker, analyze.no_llm, analyze.execute, analyze.broker) == ("NVDA", True, True, "paper")
    backtest = parser.parse_args(["backtest", "AAPL", "MSFT", "--months", "2"])
    assert (backtest.tickers, backtest.months) == (["AAPL", "MSFT"], 2)


def test_a_command_is_required():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
