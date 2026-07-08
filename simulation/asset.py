"""
simulation/asset.py

Defines the Asset data model, including the two supported return models:

1. Lognormal  - a single expected annual return + volatility. Realistic for
   equities/ETFs and a reasonable default for "quiet" holdings.
2. Regime     - a small set of discrete regimes (e.g. Bear / Base / Bull),
   each with a probability, an expected annual return, and its own
   volatility. Better suited to assets like BTC/SOL that behave very
   differently depending on the macro cycle.

Both models are driven by the same correlated standard-normal draw per
(simulation, year, asset), so cross-asset correlation is preserved
regardless of which return model an individual asset uses. See
simulation/montecarlo.py for exactly how the draw is turned into a return.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AssetClass(str, Enum):
    STOCK = "Stock"
    ETF = "ETF"
    CRYPTO = "Crypto"
    CASH = "Cash"
    GOLD = "Gold"
    CUSTOM = "Custom"


class ReturnModelType(str, Enum):
    LOGNORMAL = "lognormal"
    REGIME = "regime"


@dataclass
class Regime:
    """A single macro regime for an asset's regime-based return model."""
    name: str
    probability: float          # 0..1, all regimes for an asset must sum to 1
    expected_return: float      # annual, e.g. 0.55 = +55%
    volatility: float           # annual std dev within the regime


@dataclass
class Asset:
    """A single portfolio holding and everything needed to simulate it."""

    name: str
    symbol: str
    asset_class: AssetClass = AssetClass.CUSTOM

    allocation_pct: float = 0.0        # target allocation, 0..1 (informational + used to split DCA)
    initial_price: float = 1.0
    current_price: float = 1.0
    starting_holdings: float = 0.0     # units held today
    weekly_dca: float = 0.0            # currency/week added to THIS asset
    monthly_dca: float = 0.0           # currency/month added to THIS asset
    annual_dca_increase_pct: float = 0.0
    dca_overrides: dict[int, float] = field(default_factory=dict)  # {year: annual_amount}

    return_model: ReturnModelType = ReturnModelType.LOGNORMAL

    # Lognormal model params
    expected_return: float = 0.08
    volatility: float = 0.15

    # Regime model params
    regimes: list[Regime] = field(default_factory=list)

    rebalance_group: str = "default"

    def starting_value(self) -> float:
        return self.starting_holdings * self.current_price

    def validate(self) -> list[str]:
        """Return a list of human-readable validation problems (empty = OK)."""
        problems: list[str] = []
        if not self.name.strip():
            problems.append("Asset name cannot be empty.")
        if self.current_price <= 0:
            problems.append(f"{self.name}: current price must be > 0.")
        if self.volatility < 0:
            problems.append(f"{self.name}: volatility cannot be negative.")
        if self.return_model == ReturnModelType.REGIME:
            if not self.regimes:
                problems.append(f"{self.name}: regime model selected but no regimes defined.")
            else:
                total_prob = sum(r.probability for r in self.regimes)
                if abs(total_prob - 1.0) > 1e-6:
                    problems.append(
                        f"{self.name}: regime probabilities sum to {total_prob:.3f}, must sum to 1.0."
                    )
        return problems

    def reset_to_default(self, default: "Asset") -> None:
        """In-place reset of the editable assumption fields to a default snapshot."""
        self.allocation_pct = default.allocation_pct
        self.weekly_dca = default.weekly_dca
        self.monthly_dca = default.monthly_dca
        self.annual_dca_increase_pct = default.annual_dca_increase_pct
        self.dca_overrides = dict(default.dca_overrides)
        self.return_model = default.return_model
        self.expected_return = default.expected_return
        self.volatility = default.volatility
        self.regimes = [Regime(r.name, r.probability, r.expected_return, r.volatility) for r in default.regimes]
