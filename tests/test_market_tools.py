"""Oil-price tool: the text the model sees, with the feed mocked out."""

from app.agent.tools import market_tools
from app.market_data.client import EIAClientError


def test_summary_carries_both_benchmarks_and_dates(monkeypatch):
    monkeypatch.setattr(market_tools, "get_oil_prices", lambda: {
        "wti_usd": 61.234, "wti_date": "2026-09-04",
        "brent_usd": 65.5, "brent_date": "2026-09-04",
    })
    text = market_tools.run({})
    assert "WTI:   $61.23/bbl" in text and "Brent: $65.50/bbl" in text
    assert text.count("2026-09-04") == 2


def test_feed_outage_is_reported_not_raised(monkeypatch):
    def down():
        raise EIAClientError("HTTP 503")
    monkeypatch.setattr(market_tools, "get_oil_prices", down)
    assert "unavailable" in market_tools.run({})
