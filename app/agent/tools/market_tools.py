
from app.market_data.cache import get_oil_prices
from app.market_data.client import EIAClientError

"""Agent-callable tool: current WTI and Brent spot prices.
"""

# Nothing here overlaps the petrophysical quantities the guard watches.
MEASURES: set[str] = set()

TOOL_SCHEMA = {
    "name": "get_oil_prices",
    "description": (
        "Get today's WTI and Brent crude oil spot prices in USD per barrel "
        "from the U.S. Energy Information Administration (EIA). Use it when "
        "the user asks about the oil price, the market, or wants to relate a "
        "well's economics to current commodity prices. Takes no input."
    ),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}


# This is what the LLM sees
def summarize_prices(prices: dict) -> str:
    return (
        "Crude oil spot prices (EIA):\n"
        f"  WTI:   ${prices['wti_usd']:.2f}/bbl  (trading day {prices['wti_date']})\n"
        f"  Brent: ${prices['brent_usd']:.2f}/bbl  (trading day {prices['brent_date']})\n"
        "  These are the latest daily closes EIA has published, usually one to "
        "a few days behind today; quote the trading day with the price."
    )


def run(tool_input: dict) -> str:
    """Execute the tool. An EIA outage is reported as text for the model to
    relay, not raised -- there is no number to fall back on."""
    try:
        return summarize_prices(get_oil_prices())

    except EIAClientError as e:
        return (
            f"Oil prices are unavailable right now ({e}). Tell the user the "
            "market feed is down; do not quote a price from memory."
        )
