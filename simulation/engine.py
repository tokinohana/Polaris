"""
simulation/engine.py

Thin orchestration layer between the GUI and the numerical core. This is
the only module the GUI tabs should import from `simulation/` for running
a simulation - it validates the portfolio, runs Monte Carlo, computes
statistics, and packages everything the Charts tab needs.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from simulation.montecarlo import SimulationResult, run_simulation
from simulation.portfolio import Portfolio
from simulation.statistics import SummaryStats, max_drawdown_path, summarize


@dataclass
class EngineOutput:
    result: SimulationResult
    stats: SummaryStats
    drawdown: np.ndarray          # (n_sims, years+1)
    median_drawdown_path: np.ndarray   # (years+1,) drawdown of the median-final-value path's percentile band


class SimulationError(Exception):
    pass


def run(
    portfolio: Portfolio,
    years: int,
    n_sims: int,
    target_value: float | None = None,
    seed: int | None = None,
) -> EngineOutput:
    problems = portfolio.validate()
    if problems:
        raise SimulationError("\n".join(problems))
    if years <= 0:
        raise SimulationError("Target year must be at least 1 year out.")
    if n_sims <= 0:
        raise SimulationError("Number of simulations must be positive.")

    result = run_simulation(portfolio, years, n_sims, seed=seed)

    final_values = result.portfolio_value[:, -1]
    invested_final = float(result.invested_capital[-1])
    stats = summarize(final_values, invested_final, result.annual_returns, years, target_value)

    drawdown = max_drawdown_path(result.portfolio_value)
    median_drawdown_path = np.percentile(drawdown, 50, axis=0)

    return EngineOutput(
        result=result,
        stats=stats,
        drawdown=drawdown,
        median_drawdown_path=median_drawdown_path,
    )
