"""
simulation/montecarlo.py

The numerical core of the app. Everything here is vectorized NumPy -
there is no per-simulation Python loop, only a per-YEAR loop (years is
small, typically 5-40), which is what makes 10,000-50,000 simulations
finish in a few seconds.

Correlation method
-------------------
1. Build the asset correlation matrix (validated/repaired to be positive
   semi-definite in Portfolio.nearest_positive_semidefinite()).
2. Cholesky-decompose it: corr = L @ L.T
3. Draw independent standard-normal noise of shape (n_sims, n_years, n_assets)
   and multiply by L.T to get correlated standard-normal draws Z.
4. Turn Z into an annual return per asset:
   - Lognormal assets: return = exp(mu - 0.5*sigma^2 + sigma*Z) - 1
     (the -0.5*sigma^2 term keeps E[1+return] = exp(mu), the standard
     lognormal drift correction).
   - Regime assets: use norm.cdf(Z) as a correlated uniform draw to select
     a regime according to its cumulative probability, then return =
     regime.expected_return + regime.volatility * Z. Reusing the same Z
     for both regime selection and in-regime noise keeps the asset's
     correlation with the rest of the portfolio intact even though the
     return is regime-conditional.

This is a documented modeling approximation, not a claim of a single
"correct" way to correlate regime-switching assets - it was chosen because
it is simple, fast, vectorizable, and preserves the requested correlation
structure directionally (a bad year for one correlated asset makes a bad
regime more likely for another).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from simulation.asset import Asset, ReturnModelType
from simulation.portfolio import Portfolio, RebalanceFrequency
from utils.helpers import expand_dca_schedule


@dataclass
class SimulationResult:
    years: int
    n_sims: int
    asset_names: list[str]

    # shape (n_sims, years+1) - index 0 is "today"
    portfolio_value: np.ndarray
    invested_capital: np.ndarray          # shape (years+1,) - deterministic, same for all sims
    # shape (n_sims, years+1, n_assets)
    asset_values: np.ndarray
    # shape (n_sims, years) portfolio-level annual returns
    annual_returns: np.ndarray
    # shape (years,) total contribution made that year (sum over assets)
    annual_contributions: np.ndarray


def _draw_correlated_normals(n_sims: int, years: int, corr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    n_assets = corr.shape[0]
    L = np.linalg.cholesky(corr)
    independent = rng.standard_normal(size=(n_sims, years, n_assets))
    # (n_sims, years, n_assets) @ (n_assets, n_assets) -> correlated draws
    correlated = independent @ L.T
    return correlated


def _asset_annual_returns(asset: Asset, z: np.ndarray) -> np.ndarray:
    """z: shape (n_sims, years) - correlated standard normal draws for this asset.
    Returns an array of the same shape with annual returns (e.g. 0.12 = +12%).
    """
    if asset.return_model == ReturnModelType.LOGNORMAL:
        mu, sigma = asset.expected_return, asset.volatility
        return np.exp(mu - 0.5 * sigma ** 2 + sigma * z) - 1.0

    # Regime model
    if not asset.regimes:
        # Fall back to a flat 0% return rather than crashing.
        return np.zeros_like(z)

    u = norm.cdf(z)  # correlated uniform in (0,1)
    cum_probs = np.cumsum([r.probability for r in asset.regimes])
    cum_probs[-1] = 1.0  # guard against float drift

    returns = np.zeros_like(z)
    lower = 0.0
    for regime, upper in zip(asset.regimes, cum_probs):
        mask = (u > lower) & (u <= upper)
        returns[mask] = regime.expected_return + regime.volatility * z[mask]
        lower = upper
    return returns


def run_simulation(
    portfolio: Portfolio,
    years: int,
    n_sims: int,
    seed: int | None = None,
) -> SimulationResult:
    """Run the full correlated Monte Carlo simulation and return raw paths.

    Contribution mechanics:
      - Each asset has its own DCA schedule (weekly/monthly + annual growth,
        or explicit per-year overrides), expanded to an annual contribution
        amount for every simulated year.
      - Contributions are added to each asset's dollar value AFTER that
        year's return is applied (i.e. money invested during the year
        starts earning returns the following year - a standard, slightly
        conservative simplification for an annual-step model).

    Rebalancing:
      - Never: assets drift freely with their own returns.
      - Annual: at the end of every year, total portfolio value is
        redistributed across assets according to their target
        allocation_pct.
    """
    rng = np.random.default_rng(seed)
    assets = portfolio.assets
    n_assets = len(assets)
    corr = portfolio.nearest_positive_semidefinite()

    z = _draw_correlated_normals(n_sims, years, corr, rng)  # (n_sims, years, n_assets)

    # Per-asset annual return arrays and contribution schedules
    asset_returns = np.zeros((n_sims, years, n_assets))
    contribution_schedule = np.zeros((years, n_assets))
    for i, asset in enumerate(assets):
        raw_returns = _asset_annual_returns(asset, z[:, :, i])
        # No position can lose more than 100% of its value in a single year
        # (regime-model returns are drawn from an unbounded normal and can
        # otherwise dip below -100% in rare tail draws).
        asset_returns[:, :, i] = np.clip(raw_returns, -0.99, None)
        contribution_schedule[:, i] = expand_dca_schedule(
            asset.weekly_dca, asset.monthly_dca, asset.annual_dca_increase_pct,
            years, asset.dca_overrides,
        )

    asset_values = np.zeros((n_sims, years + 1, n_assets))
    for i, asset in enumerate(assets):
        asset_values[:, 0, i] = asset.starting_value()

    target_weights = np.array([a.allocation_pct for a in assets])
    if target_weights.sum() > 0:
        target_weights = target_weights / target_weights.sum()

    for y in range(1, years + 1):
        prev = asset_values[:, y - 1, :]
        grown = prev * (1.0 + asset_returns[:, y - 1, :])
        contributed = grown + contribution_schedule[y - 1, :]

        if portfolio.rebalance_frequency == RebalanceFrequency.ANNUAL and n_assets > 0:
            total = contributed.sum(axis=1, keepdims=True)
            contributed = total * target_weights.reshape(1, -1)

        asset_values[:, y, :] = contributed

    portfolio_value = asset_values.sum(axis=2)  # (n_sims, years+1)

    # Deterministic invested-capital track (same for every simulation path)
    starting_value = sum(a.starting_value() for a in assets)
    annual_contrib_totals = contribution_schedule.sum(axis=1)  # (years,)
    invested_capital = np.concatenate(([starting_value], starting_value + np.cumsum(annual_contrib_totals)))

    with np.errstate(divide="ignore", invalid="ignore"):
        annual_returns = np.where(
            portfolio_value[:, :-1] > 0,
            portfolio_value[:, 1:] / np.maximum(portfolio_value[:, :-1], 1e-9) - 1.0,
            0.0,
        )

    return SimulationResult(
        years=years,
        n_sims=n_sims,
        asset_names=[a.name for a in assets],
        portfolio_value=portfolio_value,
        invested_capital=invested_capital,
        asset_values=asset_values,
        annual_returns=annual_returns,
        annual_contributions=annual_contrib_totals,
    )
