"""
simulation/price_fetch.py

Fetches latest market prices via Yahoo Finance (yfinance). Crypto symbols
are mapped to their Yahoo "-USD" pair ticker; stocks/ETFs are passed
through as-is. All prices come back in USD - if your portfolio currency
is IDR, you still need an FX conversion step (not included here).
"""
from __future__ import annotations

import yfinance as yf

from simulation.asset import Asset, AssetClass

# Symbols that need mapping to a Yahoo Finance ticker.
# Extend this as you add assets that aren't already valid Yahoo tickers.
CRYPTO_TICKER_MAP = {
    "BTC": "BTC-USD",
    "SOL": "SOL-USD",
    "ETH": "ETH-USD",
}


def resolve_ticker(asset: Asset) -> str:
    if asset.asset_class == AssetClass.CRYPTO:
        return CRYPTO_TICKER_MAP.get(asset.symbol.upper(), f"{asset.symbol.upper()}-USD")
    return asset.symbol.upper()


def fetch_latest_price(asset: Asset) -> float | None:
    """Returns the latest price, or None if the fetch failed."""
    ticker_str = resolve_ticker(asset)
    try:
        ticker = yf.Ticker(ticker_str)
        price = ticker.fast_info.get("last_price")
        if price:
            return float(price)
        # Fallback: last close from 1-day history
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def fetch_all_prices(assets: list[Asset]) -> dict[str, tuple[float | None, str]]:
    """Returns {symbol: (price_or_None, ticker_used)} for every asset.
    Fetches one at a time so a single bad/delisted ticker doesn't kill the batch.
    """
    results = {}
    for asset in assets:
        ticker_str = resolve_ticker(asset)
        price = fetch_latest_price(asset)
        results[asset.symbol] = (price, ticker_str)
    return results