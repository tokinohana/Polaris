"""
simulation/statistics.py

Pure functions that turn raw Monte Carlo output arrays into the summary
statistics shown in the UI. Kept separate from the engine so it's easy to
unit test and reuse (e.g. for CSV export) without re-running simulations.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


PERCENTILES = (5, 10, 25, 50, 75, 90, 95)


@dataclass
class SummaryStats:
    minimum: float
    maximum: float
    mean: float
    median: float
    mode_estimate: float
    std_dev: float
    percentiles: dict[int, float]        # {5: ..., 10: ..., ...}
    prob_profit: float                   # P(final value > invested capital)
    prob_above_target: float | None      # P(final value > target), None if no target set
    prob_below_target: float | None
    expected_value: float
    median_cagr: float
    worst_year_return: float
    best_year_return: float


def _mode_estimate(final_values: np.ndarray, bins: int = 60) -> float:
    """Estimate the mode via a histogram peak (final values are continuous,
    so a literal mode is meaningless)."""
    counts, edges = np.histogram(final_values, bins=bins)
    peak_idx = int(np.argmax(counts))
    return float((edges[peak_idx] + edges[peak_idx + 1]) / 2.0)


def summarize(
    final_values: np.ndarray,
    invested_capital_final: float,
    annual_returns: np.ndarray,   # shape (n_sims, n_years) portfolio-level annual returns
    years: int,
    target_value: float | None = None,
) -> SummaryStats:
    """Compute the full summary statistics block for a completed simulation.

    final_values: shape (n_sims,) - ending portfolio value for each path
    invested_capital_final: total contributed (incl. starting value) by the target year
    annual_returns: portfolio-level annual returns per sim/year, used for
        median CAGR and best/worst year stats.
    """
    pct = {p: float(np.percentile(final_values, p)) for p in PERCENTILES}
    mean_val = float(np.mean(final_values))
    prob_profit = float(np.mean(final_values > invested_capital_final))

    prob_above = prob_below = None
    if target_value is not None:
        prob_above = float(np.mean(final_values > target_value))
        prob_below = float(np.mean(final_values < target_value))

    median_final = pct[50]
    if invested_capital_final > 0 and years > 0:
        median_cagr = (median_final / invested_capital_final) ** (1.0 / years) - 1.0
    else:
        median_cagr = 0.0

    return SummaryStats(
        minimum=float(np.min(final_values)),
        maximum=float(np.max(final_values)),
        mean=mean_val,
        median=median_final,
        mode_estimate=_mode_estimate(final_values),
        std_dev=float(np.std(final_values)),
        percentiles=pct,
        prob_profit=prob_profit,
        prob_above_target=prob_above,
        prob_below_target=prob_below,
        expected_value=mean_val,
        median_cagr=float(median_cagr),
        worst_year_return=float(np.min(annual_returns)),
        best_year_return=float(np.max(annual_returns)),
    )


def max_drawdown_path(value_path: np.ndarray) -> np.ndarray:
    """Given portfolio value paths (n_sims, n_years+1), return the running
    drawdown (n_sims, n_years+1) at every step: (peak_so_far - value)/peak_so_far.
    """
    running_max = np.maximum.accumulate(value_path, axis=1)
    running_max[running_max == 0] = 1e-9
    drawdown = (running_max - value_path) / running_max
    return drawdown
