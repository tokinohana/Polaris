"""
gui/assumptions_tab.py

The Assumptions Panel: every number the simulation engine actually uses is
editable here and nowhere is it hidden. For each asset: return model
(lognormal or regime), its parameters, and DCA settings. Below that: the
cross-asset correlation matrix and the rebalancing rule. A "Reset to
Default" button restores everything to the originally loaded preset.
"""
from __future__ import annotations

import copy
import tkinter as tk
from tkinter import messagebox
from typing import Callable

import ttkbootstrap as ttkb
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, X, Y, W, BOTTOM

from gui.app_state import AppState
from simulation.asset import Regime, ReturnModelType
from simulation.portfolio import RebalanceFrequency
from utils.helpers import safe_float


class AssetAssumptionPanel(ttkb.Labelframe):
    """One collapsible-looking panel per asset with its return-model fields."""

    def __init__(self, parent, asset):
        super().__init__(parent, text=f"{asset.name} ({asset.symbol})", padding=10)
        self.asset = asset

        self.model_var = tk.StringVar(value=asset.return_model.value)
        self.expected_return_var = tk.StringVar(value=f"{asset.expected_return * 100:.2f}")
        self.volatility_var = tk.StringVar(value=f"{asset.volatility * 100:.2f}")

        top = ttkb.Frame(self)
        top.pack(fill=X)
        ttkb.Label(top, text="Return Model:").pack(side=LEFT)
        model_box = ttkb.Combobox(
            top, textvariable=self.model_var, state="readonly", width=14,
            values=[m.value for m in ReturnModelType],
        )
        model_box.pack(side=LEFT, padx=(6, 20))
        model_box.bind("<<ComboboxSelected>>", lambda e: self._render_model_fields())

        self.dca_frame = ttkb.Frame(self)
        self.dca_frame.pack(fill=X, pady=(0, 6))
        self.weekly_var = tk.StringVar(value=str(asset.weekly_dca))
        self.monthly_var = tk.StringVar(value=str(asset.monthly_dca))
        self.dca_growth_var = tk.StringVar(value=f"{asset.annual_dca_increase_pct * 100:.2f}")
        for label, var in [("Weekly DCA", self.weekly_var), ("Monthly DCA", self.monthly_var),
                            ("Annual DCA Growth %", self.dca_growth_var)]:
            ttkb.Label(self.dca_frame, text=label + ":").pack(side=LEFT)
            ttkb.Entry(self.dca_frame, textvariable=var, width=10).pack(side=LEFT, padx=(4, 16))

        self.model_fields_frame = ttkb.Frame(self)
        self.model_fields_frame.pack(fill=X)

        self.regime_rows: list[dict] = []
        self.regime_rows_frame = None
        self._render_model_fields()

    def _render_model_fields(self):
        for child in self.model_fields_frame.winfo_children():
            child.destroy()

        if self.model_var.get() == ReturnModelType.LOGNORMAL.value:
            row = ttkb.Frame(self.model_fields_frame)
            row.pack(fill=X, pady=2)
            ttkb.Label(row, text="Expected Annual Return %:").pack(side=LEFT)
            ttkb.Entry(row, textvariable=self.expected_return_var, width=10).pack(side=LEFT, padx=(4, 20))
            ttkb.Label(row, text="Volatility %:").pack(side=LEFT)
            ttkb.Entry(row, textvariable=self.volatility_var, width=10).pack(side=LEFT, padx=4)
        else:
            self.regime_rows = []
            header = ttkb.Frame(self.model_fields_frame)
            header.pack(fill=X)
            for text, w in [("Regime", 12), ("Probability %", 10), ("Expected Return %", 14), ("Volatility %", 10)]:
                ttkb.Label(header, text=text, bootstyle="secondary", width=w).pack(side=LEFT)
            self.regime_rows_frame = ttkb.Frame(self.model_fields_frame)
            self.regime_rows_frame.pack(fill=X)

            source_regimes = self.asset.regimes or [Regime("Base", 1.0, self.asset.expected_return, self.asset.volatility)]
            for r in source_regimes:
                self._add_regime_row(r.name, r.probability * 100, r.expected_return * 100, r.volatility * 100)

            btn_row = ttkb.Frame(self.model_fields_frame)
            btn_row.pack(fill=X, pady=(4, 0))
            ttkb.Button(btn_row, text="+ Add Regime", bootstyle="link", command=lambda: self._add_regime_row("New", 0, 0, 20)).pack(side=LEFT)

    def _add_regime_row(self, name, prob_pct, ret_pct, vol_pct):
        row_frame = ttkb.Frame(self.regime_rows_frame)
        row_frame.pack(fill=X, pady=1)
        name_var = tk.StringVar(value=name)
        prob_var = tk.StringVar(value=f"{prob_pct:.1f}")
        ret_var = tk.StringVar(value=f"{ret_pct:.1f}")
        vol_var = tk.StringVar(value=f"{vol_pct:.1f}")
        ttkb.Entry(row_frame, textvariable=name_var, width=12).pack(side=LEFT)
        ttkb.Entry(row_frame, textvariable=prob_var, width=10).pack(side=LEFT)
        ttkb.Entry(row_frame, textvariable=ret_var, width=14).pack(side=LEFT)
        ttkb.Entry(row_frame, textvariable=vol_var, width=10).pack(side=LEFT)
        entry = {"frame": row_frame, "name": name_var, "prob": prob_var, "ret": ret_var, "vol": vol_var}

        def remove():
            row_frame.destroy()
            self.regime_rows.remove(entry)

        ttkb.Button(row_frame, text="x", bootstyle="danger-link", width=2, command=remove).pack(side=LEFT, padx=4)
        self.regime_rows.append(entry)

    def apply_to_asset(self) -> list[str]:
        """Write widget values back into self.asset. Returns validation problems."""
        problems: list[str] = []
        self.asset.return_model = ReturnModelType(self.model_var.get())
        self.asset.weekly_dca = safe_float(self.weekly_var.get())
        self.asset.monthly_dca = safe_float(self.monthly_var.get())
        self.asset.annual_dca_increase_pct = safe_float(self.dca_growth_var.get()) / 100.0

        if self.asset.return_model == ReturnModelType.LOGNORMAL:
            self.asset.expected_return = safe_float(self.expected_return_var.get()) / 100.0
            self.asset.volatility = safe_float(self.volatility_var.get()) / 100.0
            self.asset.regimes = []
        else:
            regimes = []
            total_prob = 0.0
            for row in self.regime_rows:
                prob = safe_float(row["prob"].get()) / 100.0
                regimes.append(Regime(
                    name=row["name"].get().strip() or "Regime",
                    probability=prob,
                    expected_return=safe_float(row["ret"].get()) / 100.0,
                    volatility=safe_float(row["vol"].get()) / 100.0,
                ))
                total_prob += prob
            if regimes and abs(total_prob - 1.0) > 0.01:
                problems.append(f"{self.asset.name}: regime probabilities sum to {total_prob*100:.1f}%, should be 100%.")
            self.asset.regimes = regimes
        return problems


class AssumptionsTab(ttkb.Frame):
    def __init__(self, parent, state: AppState, on_portfolio_changed: Callable[[], None]):
        super().__init__(parent, padding=12)
        self.state = state
        self.on_portfolio_changed = on_portfolio_changed
        self.asset_panels: list[AssetAssumptionPanel] = []
        self.corr_entries: dict[tuple[int, int], tk.StringVar] = {}
        self._build_static()
        self.refresh()

    def _build_static(self):
        top = ttkb.Frame(self)
        top.pack(fill=X, pady=(0, 8))
        ttkb.Label(top, text="Assumptions Panel", font=("-size", 14, "-weight", "bold")).pack(side=LEFT)

        ttkb.Button(top, text="Apply Changes", bootstyle="success", command=self._apply).pack(side=RIGHT, padx=3)
        ttkb.Button(top, text="Reset to Default", bootstyle="warning-outline", command=self._reset).pack(side=RIGHT, padx=3)

        rebal_row = ttkb.Frame(self)
        rebal_row.pack(fill=X, pady=(0, 8))
        ttkb.Label(rebal_row, text="Rebalancing:").pack(side=LEFT)
        self.rebal_var = tk.StringVar(value=self.state.portfolio.rebalance_frequency.value)
        ttkb.Combobox(
            rebal_row, textvariable=self.rebal_var, state="readonly", width=14,
            values=[f.value for f in RebalanceFrequency],
        ).pack(side=LEFT, padx=6)

        # Scrollable area for per-asset panels
        container = ttkb.Frame(self)
        container.pack(fill=BOTH, expand=True)
        self.canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttkb.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttkb.Frame(self.canvas)
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.corr_frame = ttkb.Labelframe(self, text="Correlation Matrix", padding=10)
        self.corr_frame.pack(fill=X, pady=(8, 0))

    def refresh(self):
        for panel in self.asset_panels:
            panel.destroy()
        self.asset_panels = []
        for asset in self.state.portfolio.assets:
            panel = AssetAssumptionPanel(self.scroll_frame, asset)
            panel.pack(fill=X, pady=4, padx=2)
            self.asset_panels.append(panel)

        self._build_correlation_grid()
        self.rebal_var.set(self.state.portfolio.rebalance_frequency.value)

    def _build_correlation_grid(self):
        for child in self.corr_frame.winfo_children():
            child.destroy()
        self.corr_entries = {}

        assets = self.state.portfolio.assets
        n = len(assets)
        if n == 0:
            ttkb.Label(self.corr_frame, text="Add assets to configure correlation.").pack()
            return

        ttkb.Label(self.corr_frame, text="").grid(row=0, column=0)
        for j, a in enumerate(assets):
            ttkb.Label(self.corr_frame, text=a.symbol, bootstyle="secondary").grid(row=0, column=j + 1, padx=4)

        for i, a in enumerate(assets):
            ttkb.Label(self.corr_frame, text=a.symbol, bootstyle="secondary").grid(row=i + 1, column=0, padx=4, sticky=W)
            for j in range(n):
                if j < i:
                    continue  # only render upper triangle incl diagonal
                if i == j:
                    ttkb.Label(self.corr_frame, text="1.00").grid(row=i + 1, column=j + 1, padx=2, pady=1)
                else:
                    var = tk.StringVar(value=f"{self.state.portfolio.correlation[i, j]:.2f}")
                    ttkb.Entry(self.corr_frame, textvariable=var, width=6).grid(row=i + 1, column=j + 1, padx=2, pady=1)
                    self.corr_entries[(i, j)] = var

    def _apply(self):
        problems: list[str] = []
        for panel in self.asset_panels:
            problems.extend(panel.apply_to_asset())

        for (i, j), var in self.corr_entries.items():
            self.state.portfolio.set_correlation(i, j, safe_float(var.get()))

        self.state.portfolio.rebalance_frequency = RebalanceFrequency(self.rebal_var.get())

        if problems:
            messagebox.showwarning("Check Assumptions", "\n".join(problems))
        else:
            messagebox.showinfo("Applied", "Assumptions updated. Run a simulation to see the effect.")
        self.on_portfolio_changed()

    def _reset(self):
        if self.state.default_portfolio_snapshot is None:
            messagebox.showinfo("No Default", "No default snapshot is available to reset to.")
            return
        if not messagebox.askyesno("Reset to Default", "This will discard your assumption edits. Continue?"):
            return
        default = self.state.default_portfolio_snapshot
        for asset, default_asset in zip(self.state.portfolio.assets, default.assets):
            if asset.symbol == default_asset.symbol:
                asset.reset_to_default(default_asset)
        self.state.portfolio.correlation = copy.deepcopy(default.correlation)
        self.state.portfolio.rebalance_frequency = default.rebalance_frequency
        self.refresh()
        self.on_portfolio_changed()
