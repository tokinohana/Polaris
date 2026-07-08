"""
gui/portfolio_tab.py

Portfolio Builder tab: a table of assets plus dialogs to add/edit them,
and controls to load a preset or save/load a portfolio to/from disk.
"""
from __future__ import annotations

import copy
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable

import threading
from simulation.price_fetch import fetch_all_prices

import ttkbootstrap as ttkb
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, X, Y, W

from gui.app_state import AppState
from simulation.asset import Asset, AssetClass, ReturnModelType
from simulation.presets import load_portfolio, save_portfolio
from utils.helpers import format_currency, safe_float


class AssetDialog(ttkb.Toplevel):
    """Modal dialog for adding or editing a single Asset's structural fields."""

    def __init__(self, parent, asset: Asset | None, on_save: Callable[[Asset], None]):
        super().__init__(parent)
        self.title("Edit Asset" if asset else "Add Asset")
        self.on_save = on_save
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.existing = asset
        a = asset or Asset(name="", symbol="", asset_class=AssetClass.CUSTOM)

        self.vars = {
            "name": tk.StringVar(value=a.name),
            "symbol": tk.StringVar(value=a.symbol),
            "asset_class": tk.StringVar(value=a.asset_class.value),
            "allocation_pct": tk.StringVar(value=f"{a.allocation_pct * 100:.2f}"),
            "current_price": tk.StringVar(value=str(a.current_price)),
            "starting_holdings": tk.StringVar(value=str(a.starting_holdings)),
            "weekly_dca": tk.StringVar(value=str(a.weekly_dca)),
            "monthly_dca": tk.StringVar(value=str(a.monthly_dca)),
            "annual_dca_increase_pct": tk.StringVar(value=f"{a.annual_dca_increase_pct * 100:.2f}"),
        }

        rows = [
            ("Name", "name"),
            ("Symbol", "symbol"),
            ("Allocation % (target)", "allocation_pct"),
            ("Current Price", "current_price"),
            ("Starting Holdings (units)", "starting_holdings"),
            ("Weekly DCA ($)", "weekly_dca"),
            ("Monthly DCA ($)", "monthly_dca"),
            ("Annual DCA Increase %", "annual_dca_increase_pct"),
        ]

        form = ttkb.Frame(self, padding=16)
        form.pack(fill=BOTH, expand=True)

        ttkb.Label(form, text="Asset Class").grid(row=0, column=0, sticky=W, pady=4)
        ttkb.Combobox(
            form, textvariable=self.vars["asset_class"],
            values=[c.value for c in AssetClass], state="readonly", width=28,
        ).grid(row=0, column=1, pady=4, sticky=W)

        for i, (label, key) in enumerate(rows, start=1):
            ttkb.Label(form, text=label).grid(row=i, column=0, sticky=W, pady=4)
            ttkb.Entry(form, textvariable=self.vars[key], width=30).grid(row=i, column=1, pady=4, sticky=W)

        note = ttkb.Label(
            form,
            text="Return model, volatility, and regimes are set in the Assumptions tab.",
            bootstyle="secondary", wraplength=340,
        )
        note.grid(row=len(rows) + 1, column=0, columnspan=2, pady=(10, 0), sticky=W)

        btns = ttkb.Frame(form)
        btns.grid(row=len(rows) + 2, column=0, columnspan=2, pady=(16, 0), sticky="e")
        ttkb.Button(btns, text="Cancel", bootstyle="secondary", command=self.destroy).pack(side=RIGHT, padx=4)
        ttkb.Button(btns, text="Save", bootstyle="success", command=self._save).pack(side=RIGHT, padx=4)

    def _save(self):
        try:
            asset = self.existing or Asset(name="", symbol="")
            asset.name = self.vars["name"].get().strip()
            asset.symbol = self.vars["symbol"].get().strip().upper()
            asset.asset_class = AssetClass(self.vars["asset_class"].get())
            asset.allocation_pct = safe_float(self.vars["allocation_pct"].get()) / 100.0
            asset.current_price = safe_float(self.vars["current_price"].get())
            asset.starting_holdings = safe_float(self.vars["starting_holdings"].get())
            asset.weekly_dca = safe_float(self.vars["weekly_dca"].get())
            asset.monthly_dca = safe_float(self.vars["monthly_dca"].get())
            asset.annual_dca_increase_pct = safe_float(self.vars["annual_dca_increase_pct"].get()) / 100.0

            if not asset.name:
                messagebox.showerror("Invalid Asset", "Name cannot be empty.", parent=self)
                return
            if asset.current_price <= 0:
                messagebox.showerror("Invalid Asset", "Current price must be > 0.", parent=self)
                return

            self.on_save(asset)
            self.destroy()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc), parent=self)


class PortfolioTab(ttkb.Frame):
    def __init__(self, parent, state: AppState, on_portfolio_changed: Callable[[], None]):
        super().__init__(parent, padding=12)
        self.state = state
        self.on_portfolio_changed = on_portfolio_changed
        self._build()
        self.refresh()

    def _build(self):
        top = ttkb.Frame(self)
        top.pack(fill=X, pady=(0, 8))

        ttkb.Label(top, text="Portfolio Builder", font=("-size", 14, "-weight", "bold")).pack(side=LEFT)

        btns = ttkb.Frame(self)
        btns.pack(fill=X, pady=(0, 8))
        ttkb.Button(btns, text="Add Asset", bootstyle="success", command=self._add_asset).pack(side=LEFT, padx=3)
        ttkb.Button(btns, text="Edit Selected", command=self._edit_asset).pack(side=LEFT, padx=3)
        ttkb.Button(btns, text="Remove Selected", bootstyle="danger-outline", command=self._remove_asset).pack(side=LEFT, padx=3)
        ttkb.Separator(btns, orient="vertical").pack(side=LEFT, fill=Y, padx=8)
        ttkb.Button(btns, text="Save Portfolio...", command=self._save_portfolio).pack(side=LEFT, padx=3)
        ttkb.Button(btns, text="Load Portfolio...", command=self._load_portfolio).pack(side=LEFT, padx=3)
        ttkb.Button(btns, text="Refresh Prices", bootstyle="info", command=self._refresh_prices).pack(side=LEFT, padx=3)

        columns = ("class", "alloc", "price", "holdings", "value", "weekly", "monthly", "model")
        self.tree = ttkb.Treeview(self, columns=columns, show="tree headings", height=10, bootstyle="primary")
        self.tree.heading("#0", text="Asset")
        self.tree.heading("class", text="Class")
        self.tree.heading("alloc", text="Alloc %")
        self.tree.heading("price", text="Price")
        self.tree.heading("holdings", text="Holdings")
        self.tree.heading("value", text="Value")
        self.tree.heading("weekly", text="Weekly DCA")
        self.tree.heading("monthly", text="Monthly DCA")
        self.tree.heading("model", text="Return Model")
        for col, w in zip(columns, (90, 70, 90, 90, 100, 90, 90, 90)):
            self.tree.column(col, width=w, anchor="e")
        self.tree.column("#0", width=140, anchor="w")
        self.tree.pack(fill=BOTH, expand=True)

        bottom = ttkb.Frame(self)
        bottom.pack(fill=X, pady=(8, 0))
        self.total_label = ttkb.Label(bottom, text="", font=("-size", 10, "-weight", "bold"))
        self.total_label.pack(side=LEFT)

    def _selected_asset(self) -> Asset | None:
        sel = self.tree.selection()
        if not sel:
            return None
        idx = int(sel[0])
        return self.state.portfolio.assets[idx]

    def _add_asset(self):
        def save(asset: Asset):
            self.state.portfolio.assets.append(asset)
            self.state.portfolio.sync_correlation_shape()
            self.refresh()
            self.on_portfolio_changed()
        AssetDialog(self, None, save)

    def _edit_asset(self):
        asset = self._selected_asset()
        if asset is None:
            messagebox.showinfo("No Selection", "Select an asset to edit.")
            return
        def save(_asset: Asset):
            self.refresh()
            self.on_portfolio_changed()
        AssetDialog(self, asset, save)

    def _remove_asset(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select an asset to remove.")
            return
        idx = int(sel[0])
        del self.state.portfolio.assets[idx]
        self.state.portfolio.sync_correlation_shape()
        self.refresh()
        self.on_portfolio_changed()

    def _save_portfolio(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        save_portfolio(self.state.portfolio, path)
        messagebox.showinfo("Saved", f"Portfolio saved to {path}")

    def _load_portfolio(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            self.state.portfolio = load_portfolio(path)
            self.state.default_portfolio_snapshot = copy.deepcopy(self.state.portfolio)
            self.refresh()
            self.on_portfolio_changed()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Load Failed", str(exc))

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        currency = self.state.portfolio.currency
        for i, a in enumerate(self.state.portfolio.assets):
            self.tree.insert(
                "", "end", iid=str(i), text=f"{a.name} ({a.symbol})",
                values=(
                    a.asset_class.value,
                    f"{a.allocation_pct * 100:.1f}%",
                    format_currency(a.current_price, currency),
                    f"{a.starting_holdings:g}",
                    format_currency(a.starting_value(), currency),
                    format_currency(a.weekly_dca, currency),
                    format_currency(a.monthly_dca, currency),
                    a.return_model.value,
                ),
            )
        total_alloc = self.state.portfolio.total_allocation() * 100
        color = "success" if abs(total_alloc - 100) < 1 else "danger"
        self.total_label.configure(
            text=f"Total Allocation: {total_alloc:.1f}%  |  Total Starting Value: "
                 f"{format_currency(self.state.portfolio.total_starting_value(), currency)}",
            bootstyle=color,
        )
        
    def _refresh_prices(self):
        if not self.state.portfolio.assets:
            return
        self._refresh_btn_state("disabled")
        threading.Thread(target=self._refresh_prices_worker, daemon=True).start()

    def _refresh_prices_worker(self):
        results = fetch_all_prices(self.state.portfolio.assets)
        self.after(0, lambda: self._apply_fetched_prices(results))

    def _apply_fetched_prices(self, results):
        failed = []
        for asset in self.state.portfolio.assets:
            price, ticker_used = results.get(asset.symbol, (None, ""))
            if price:
                asset.current_price = price
            else:
                failed.append(f"{asset.symbol} ({ticker_used})")
        self.refresh()
        self.on_portfolio_changed()
        self._refresh_btn_state("normal")
        if failed:
            messagebox.showwarning("Some Prices Failed", "Could not fetch: " + ", ".join(failed))

    def _refresh_btn_state(self, state):
        for child in self.winfo_children():
            pass  # or just keep a reference to the button in _build() and toggle it directly
