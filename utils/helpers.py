"""
utils/helpers.py

Small, dependency-free helper functions shared across the app:
currency formatting, DCA schedule expansion, and safe numeric parsing.
"""
from __future__ import annotations

from typing import Dict


CURRENCY_SYMBOLS: Dict[str, str] = {
    "IDR": "Rp",
    "USD": "$",
    "JPY": "¥",
    "EUR": "€",
}


def format_currency(value: float, currency: str = "USD") -> str:
    """Format a numeric value as a currency string with thousands separators.

    IDR is formatted with no decimal places (standard convention), all
    other currencies with two decimal places.
    """
    symbol = CURRENCY_SYMBOLS.get(currency, "")
    if currency == "IDR":
        return f"{symbol} {value:,.0f}"
    return f"{symbol}{value:,.2f}"


def format_pct(value: float, decimals: int = 1) -> str:
    """Format a fraction (0.12) as a percentage string ('12.0%')."""
    return f"{value * 100:.{decimals}f}%"


def safe_float(text: str, default: float = 0.0) -> float:
    """Parse a string to float, tolerating commas and blank input."""
    if text is None:
        return default
    text = str(text).strip().replace(",", "")
    if text == "":
        return default
    try:
        return float(text)
    except ValueError:
        return default


def safe_int(text: str, default: int = 0) -> int:
    try:
        return int(float(str(text).strip()))
    except (ValueError, TypeError):
        return default


def expand_dca_schedule(
    base_weekly: float,
    base_monthly: float,
    annual_increase_pct: float,
    years: int,
    overrides: Dict[int, float] | None = None,
) -> list[float]:
    """Expand a DCA schedule into a list of *annual contribution totals*,
    one entry per year (index 0 = year 1).

    - base_weekly / base_monthly are combined into an equivalent annual
      contribution (52 weeks, 12 months), then grown each year by
      annual_increase_pct (compounding).
    - overrides is an optional {year_number: annual_amount} dict that
      replaces the computed value for specific years (1-indexed), enabling
      the "custom schedule" use case from the spec
      (e.g. Year 1 100k/week, Year 2 150k/week, ...).
    """
    overrides = overrides or {}
    schedule: list[float] = []
    annual_base = base_weekly * 52.0 + base_monthly * 12.0
    for year in range(1, years + 1):
        if year in overrides:
            schedule.append(overrides[year])
        else:
            grown = annual_base * ((1.0 + annual_increase_pct) ** (year - 1))
            schedule.append(grown)
    return schedule
