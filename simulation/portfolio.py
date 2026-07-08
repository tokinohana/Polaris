"""
simulation/portfolio.py

Portfolio = a named collection of Assets, a correlation matrix between
them, and portfolio-level settings (rebalancing behaviour, currency).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from simulation.asset import Asset


class RebalanceFrequency(str, Enum):
    NEVER = "Never"
    ANNUAL = "Annual"


@dataclass
class Portfolio:
    name: str = "My Portfolio"
    currency: str = "USD"
    assets: list[Asset] = field(default_factory=list)

    # correlation[i][j] between assets[i] and assets[j], symmetric, diag = 1
    correlation: np.ndarray | None = None

    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.NEVER

    def __post_init__(self):
        if self.correlation is None:
            self.correlation = self._identity_correlation()

    def _identity_correlation(self) -> np.ndarray:
        n = len(self.assets)
        return np.eye(n)

    def sync_correlation_shape(self) -> None:
        """Resize the correlation matrix (preserving existing values) after
        assets are added/removed."""
        n = len(self.assets)
        if self.correlation is None or self.correlation.shape != (n, n):
            new_corr = np.eye(n)
            if self.correlation is not None:
                old_n = self.correlation.shape[0]
                m = min(old_n, n)
                new_corr[:m, :m] = self.correlation[:m, :m]
            self.correlation = new_corr

    def set_correlation(self, i: int, j: int, value: float) -> None:
        value = float(np.clip(value, -0.99, 0.99))
        self.correlation[i, j] = value
        self.correlation[j, i] = value

    def nearest_positive_semidefinite(self) -> np.ndarray:
        """Higham-style projection so a user-entered (possibly inconsistent)
        correlation matrix is always safe to Cholesky-decompose.
        Clips negative eigenvalues to a small positive floor, then
        renormalizes to unit diagonal.
        """
        corr = self.correlation.copy()
        corr = (corr + corr.T) / 2.0
        eigvals, eigvecs = np.linalg.eigh(corr)
        eigvals_clipped = np.clip(eigvals, 1e-8, None)
        fixed = eigvecs @ np.diag(eigvals_clipped) @ eigvecs.T
        d = np.sqrt(np.diag(fixed))
        d[d == 0] = 1e-8
        fixed = fixed / np.outer(d, d)
        np.fill_diagonal(fixed, 1.0)
        return fixed

    def total_allocation(self) -> float:
        return sum(a.allocation_pct for a in self.assets)

    def total_starting_value(self) -> float:
        return sum(a.starting_value() for a in self.assets)

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.assets:
            problems.append("Portfolio has no assets.")
        for a in self.assets:
            problems.extend(a.validate())
        alloc = self.total_allocation()
        if abs(alloc - 1.0) > 0.01:
            problems.append(f"Total allocation is {alloc*100:.1f}%, expected ~100%.")
        return problems

    def asset_names(self) -> list[str]:
        return [a.name for a in self.assets]
