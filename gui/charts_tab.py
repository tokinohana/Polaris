"""
gui/charts_tab.py

Displays the chart selected in the dropdown, embedded via
FigureCanvasTkAgg (with the standard Matplotlib navigation toolbar for
pan/zoom/PNG export "for free"). Also provides a CSV export of the
underlying simulation data.
"""
from __future__ import annotations

import csv
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
import ttkbootstrap as ttkb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, X, W

from charts import charts as chart_builders
from gui.app_state import AppState

CHART_OPTIONS = {
    "Portfolio Growth (Fan Chart)": chart_builders.fan_chart,
    "Distribution of Final Values (Histogram)": chart_builders.histogram_chart,
    "Drawdown Over Time": chart_builders.drawdown_chart,
    "Invested Capital vs. Portfolio Value": chart_builders.contribution_vs_value_chart,
}


class ChartsTab(ttkb.Frame):
    def __init__(self, parent, state: AppState):
        super().__init__(parent, padding=12)
        self.state = state
        self.canvas = None
        self.toolbar = None
        self._build()
        state.on_simulation_complete(lambda output: self._render(self.chart_var.get()))

    def _build(self):
        top = ttkb.Frame(self)
        top.pack(fill=X, pady=(0, 8))
        ttkb.Label(top, text="Charts", font=("-size", 14, "-weight", "bold")).pack(side=LEFT)

        self.chart_var = tk.StringVar(value=list(CHART_OPTIONS.keys())[0])
        combo = ttkb.Combobox(top, textvariable=self.chart_var, values=list(CHART_OPTIONS.keys()),
                               state="readonly", width=38)
        combo.pack(side=LEFT, padx=12)
        combo.bind("<<ComboboxSelected>>", lambda e: self._render(self.chart_var.get()))

        ttkb.Button(top, text="Export Simulation Data (CSV)", command=self._export_csv).pack(side=RIGHT)

        self.chart_container = ttkb.Frame(self)
        self.chart_container.pack(fill=BOTH, expand=True)

        self.placeholder = ttkb.Label(
            self.chart_container,
            text="Run a simulation in the Simulation tab to see charts here.",
            bootstyle="secondary",
        )
        self.placeholder.pack(expand=True)

    def _render(self, chart_name: str):
        if self.state.output is None:
            return
        self.placeholder.pack_forget()
        for child in self.chart_container.winfo_children():
            child.destroy()

        builder = CHART_OPTIONS[chart_name]
        currency = self.state.portfolio.currency
        if builder is chart_builders.histogram_chart:
            fig = builder(self.state.output, currency, self.state.target_value)
        else:
            fig = builder(self.state.output, currency)

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        toolbar_frame = ttkb.Frame(self.chart_container)
        toolbar_frame.pack(side="bottom", fill=X)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        canvas.get_tk_widget().pack(fill=BOTH, expand=True)
        self.canvas = canvas

    def _export_csv(self):
        if self.state.output is None:
            messagebox.showinfo("No Data", "Run a simulation first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return

        output = self.state.output
        pv = output.result.portfolio_value
        years_axis = np.arange(pv.shape[1])
        p5 = np.percentile(pv, 5, axis=0)
        p25 = np.percentile(pv, 25, axis=0)
        p50 = np.percentile(pv, 50, axis=0)
        p75 = np.percentile(pv, 75, axis=0)
        p95 = np.percentile(pv, 95, axis=0)
        median_dd = np.percentile(output.drawdown, 50, axis=0)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Year", "Invested_Capital", "P5", "P25", "Median", "P75", "P95", "Median_Drawdown_Pct"])
            for y in years_axis:
                writer.writerow([
                    int(y), output.result.invested_capital[y],
                    p5[y], p25[y], p50[y], p75[y], p95[y], median_dd[y] * 100,
                ])
            writer.writerow([])
            writer.writerow(["Summary Statistic", "Value"])
            s = output.stats
            for label, val in [
                ("Minimum", s.minimum), ("Maximum", s.maximum), ("Mean", s.mean),
                ("Median", s.median), ("Std Dev", s.std_dev),
                ("P5", s.percentiles[5]), ("P10", s.percentiles[10]), ("P25", s.percentiles[25]),
                ("P75", s.percentiles[75]), ("P90", s.percentiles[90]), ("P95", s.percentiles[95]),
                ("Prob Profit", s.prob_profit), ("Median CAGR", s.median_cagr),
            ]:
                writer.writerow([label, val])

        messagebox.showinfo("Exported", f"Simulation data exported to {path}")
