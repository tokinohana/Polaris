"""
gui/simulation_tab.py

Where the user actually runs the Monte Carlo simulation and sees the
statistical summary. The simulation runs on a background thread so the
UI stays responsive (important at 50,000 simulations, though the engine
is fast enough that this is mostly a safety margin).
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttkb
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, X, W

from gui.app_state import AppState
from simulation.engine import SimulationError, run
from utils.helpers import format_currency, format_pct, safe_float, safe_int

SIM_COUNT_OPTIONS = ["100", "500", "1000", "5000", "10000", "25000", "50000"]


class SimulationTab(ttkb.Frame):
    def __init__(self, parent, state: AppState):
        super().__init__(parent, padding=12)
        self.state = state
        self._build()

    def _build(self):
        ttkb.Label(self, text="Run Simulation", font=("-size", 14, "-weight", "bold")).pack(anchor=W, pady=(0, 8))

        controls = ttkb.Frame(self)
        controls.pack(fill=X, pady=(0, 8))

        ttkb.Label(controls, text="Target Year (from today):").grid(row=0, column=0, sticky=W, padx=4, pady=4)
        self.years_var = tk.StringVar(value=str(self.state.years))
        ttkb.Entry(controls, textvariable=self.years_var, width=10).grid(row=0, column=1, sticky=W, padx=4)

        ttkb.Label(controls, text="Number of Simulations:").grid(row=0, column=2, sticky=W, padx=(20, 4))
        self.n_sims_var = tk.StringVar(value=str(self.state.n_sims))
        ttkb.Combobox(controls, textvariable=self.n_sims_var, values=SIM_COUNT_OPTIONS, state="readonly", width=10).grid(row=0, column=3, sticky=W, padx=4)

        ttkb.Label(controls, text="Target Portfolio Value (optional):").grid(row=1, column=0, sticky=W, padx=4, pady=4)
        self.target_var = tk.StringVar(value="")
        ttkb.Entry(controls, textvariable=self.target_var, width=18).grid(row=1, column=1, sticky=W, padx=4)

        ttkb.Label(controls, text="Random Seed (optional, for repeatability):").grid(row=1, column=2, sticky=W, padx=(20, 4))
        self.seed_var = tk.StringVar(value=str(self.state.seed) if self.state.seed is not None else "")
        ttkb.Entry(controls, textvariable=self.seed_var, width=10).grid(row=1, column=3, sticky=W, padx=4)

        self.run_btn = ttkb.Button(self, text="Run Simulation", bootstyle="success", command=self._run_clicked)
        self.run_btn.pack(anchor=W, pady=(4, 8))

        self.progress = ttkb.Progressbar(self, mode="indeterminate", bootstyle="success-striped")
        self.status_label = ttkb.Label(self, text="", bootstyle="secondary")
        self.status_label.pack(anchor=W)

        self.results_frame = ttkb.Labelframe(self, text="Statistical Summary", padding=12)
        self.results_frame.pack(fill=BOTH, expand=True, pady=(8, 0))
        self.results_label = ttkb.Label(self.results_frame, text="Run a simulation to see results here.", justify=LEFT)
        self.results_label.pack(anchor=W)

    def _run_clicked(self):
        problems = self.state.portfolio.validate()
        if problems:
            messagebox.showerror("Cannot Run Simulation", "\n".join(problems))
            return

        years = safe_int(self.years_var.get(), 15)
        n_sims = safe_int(self.n_sims_var.get(), 10000)
        target_text = self.target_var.get().strip()
        target_value = safe_float(target_text) if target_text else None
        seed_text = self.seed_var.get().strip()
        seed = safe_int(seed_text) if seed_text else None

        self.state.years = years
        self.state.n_sims = n_sims
        self.state.target_value = target_value
        self.state.seed = seed

        self.run_btn.configure(state="disabled")
        self.progress.pack(fill=X, pady=(0, 4))
        self.progress.start(12)
        self.status_label.configure(text=f"Running {n_sims:,} simulations over {years} years...")

        thread = threading.Thread(target=self._run_in_background, args=(years, n_sims, target_value, seed), daemon=True)
        thread.start()

    def _run_in_background(self, years, n_sims, target_value, seed):
        t0 = time.time()
        try:
            output = run(self.state.portfolio, years, n_sims, target_value, seed)
            elapsed = time.time() - t0
            self.after(0, lambda: self._on_success(output, elapsed))
        except SimulationError as exc:
            self.after(0, lambda: self._on_error(str(exc)))
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._on_error(f"Unexpected error: {exc}"))

    def _on_success(self, output, elapsed):
        self.progress.stop()
        self.progress.pack_forget()
        self.run_btn.configure(state="normal")
        self.status_label.configure(text=f"Completed {output.result.n_sims:,} simulations in {elapsed:.2f}s.")
        self._render_stats(output)
        self.state.publish_result(output)

    def _on_error(self, message: str):
        self.progress.stop()
        self.progress.pack_forget()
        self.run_btn.configure(state="normal")
        self.status_label.configure(text="Simulation failed.")
        messagebox.showerror("Simulation Error", message)

    def _render_stats(self, output):
        s = output.stats
        currency = self.state.portfolio.currency
        lines = [
            f"Years simulated: {output.result.years}   |   Simulations: {output.result.n_sims:,}",
            "",
            f"Median Final Value:      {format_currency(s.median, currency)}",
            f"Mean (Expected Value):   {format_currency(s.expected_value, currency)}",
            f"Minimum / Maximum:       {format_currency(s.minimum, currency)}  /  {format_currency(s.maximum, currency)}",
            f"Std Deviation:           {format_currency(s.std_dev, currency)}",
            "",
            "Percentiles:",
            f"  5th:  {format_currency(s.percentiles[5], currency)}      25th: {format_currency(s.percentiles[25], currency)}",
            f"  50th: {format_currency(s.percentiles[50], currency)}      75th: {format_currency(s.percentiles[75], currency)}",
            f"  90th: {format_currency(s.percentiles[90], currency)}      95th: {format_currency(s.percentiles[95], currency)}",
            "",
            f"Probability of Profit:        {format_pct(s.prob_profit)}",
        ]
        if s.prob_above_target is not None:
            lines.append(f"Probability > Target:         {format_pct(s.prob_above_target)}")
            lines.append(f"Probability < Target:         {format_pct(s.prob_below_target)}")
        lines += [
            "",
            f"Median CAGR:                  {format_pct(s.median_cagr)}",
            f"Worst / Best Single-Year Return: {format_pct(s.worst_year_return)}  /  {format_pct(s.best_year_return)}",
            f"Invested Capital (by target year): {format_currency(output.result.invested_capital[-1], currency)}",
        ]
        self.results_label.configure(text="\n".join(lines), font=("Courier", 10))
