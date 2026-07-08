"""
gui/app_state.py

A small shared-state object so the four tabs can see the same Portfolio
and the most recent simulation output without importing each other
directly. Each tab that cares about new results registers a callback via
`on_simulation_complete`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from simulation.engine import EngineOutput
from simulation.portfolio import Portfolio
from simulation.presets import load_default_portfolio


@dataclass
class AppState:
    portfolio: Portfolio = field(default_factory=load_default_portfolio)
    default_portfolio_snapshot: Portfolio = field(default=None)  # for "Reset to Default"
    output: EngineOutput | None = None

    years: int = 15
    n_sims: int = 10000
    target_value: float | None = None
    seed: int | None = 42

    _listeners: list[Callable[[EngineOutput], None]] = field(default_factory=list)

    def on_simulation_complete(self, callback: Callable[[EngineOutput], None]) -> None:
        self._listeners.append(callback)

    def publish_result(self, output: EngineOutput) -> None:
        self.output = output
        for cb in self._listeners:
            cb(output)
