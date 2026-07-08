"""
main.py

Monte Carlo Portfolio Simulator - entry point.

Run with:  python main.py

Loads the default preset (your Bucket 2: BTC/SOL/SPY/MSFT/NVDA) into a
shared AppState, then builds a four-tab ttkbootstrap window: Portfolio,
Assumptions, Simulation, Charts. All simulation math lives in
simulation/; all plotting lives in charts/; this file only wires up the
GUI shell.
"""
from __future__ import annotations

import copy

import ttkbootstrap as ttkb
from ttkbootstrap.constants import BOTH

from gui.app_state import AppState
from gui.assumptions_tab import AssumptionsTab
from gui.charts_tab import ChartsTab
from gui.portfolio_tab import PortfolioTab
from gui.simulation_tab import SimulationTab


class App(ttkb.Window):
    def __init__(self):
        super().__init__(title="Monte Carlo Portfolio Simulator", themename="darkly", size=(1100, 780))

        self.state_obj = AppState()
        self.state_obj.default_portfolio_snapshot = copy.deepcopy(self.state_obj.portfolio)

        notebook = ttkb.Notebook(self)
        notebook.pack(fill=BOTH, expand=True, padx=8, pady=8)

        self.portfolio_tab = PortfolioTab(notebook, self.state_obj, self._on_portfolio_changed)
        self.assumptions_tab = AssumptionsTab(notebook, self.state_obj, self._on_portfolio_changed)
        self.simulation_tab = SimulationTab(notebook, self.state_obj)
        self.charts_tab = ChartsTab(notebook, self.state_obj)

        notebook.add(self.portfolio_tab, text="  Portfolio Builder  ")
        notebook.add(self.assumptions_tab, text="  Assumptions  ")
        notebook.add(self.simulation_tab, text="  Simulation  ")
        notebook.add(self.charts_tab, text="  Charts  ")

    def _on_portfolio_changed(self):
        """Keep both editor tabs in sync whenever assets/assumptions change
        in either one (e.g. adding an asset in Portfolio must add a row to
        the Assumptions correlation grid)."""
        self.portfolio_tab.refresh()
        self.assumptions_tab.refresh()


if __name__ == "__main__":
    app = App()
    app.mainloop()
