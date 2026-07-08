"""
charts/charts.py

Matplotlib figure builders. Each function returns a fully-built Figure so
the GUI layer just has to embed it (FigureCanvasTkAgg) - no plotting logic
lives in gui/.
"""
from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from simulation.engine import EngineOutput
from utils.helpers import format_currency


BAND_ALPHA_OUTER = 0.18
BAND_ALPHA_INNER = 0.32


def fan_chart(output: EngineOutput, currency: str = "USD") -> Figure:
    """Portfolio growth fan chart: median line with 5-95% and 25-75% bands."""
    pv = output.result.portfolio_value  # (n_sims, years+1)
    years_axis = np.arange(pv.shape[1])

    p5 = np.percentile(pv, 5, axis=0)
    p25 = np.percentile(pv, 25, axis=0)
    p50 = np.percentile(pv, 50, axis=0)
    p75 = np.percentile(pv, 75, axis=0)
    p95 = np.percentile(pv, 95, axis=0)

    fig = Figure(figsize=(7.5, 4.8), dpi=100)
    ax = fig.add_subplot(111)
    ax.fill_between(years_axis, p5, p95, alpha=BAND_ALPHA_OUTER, color="#3b82f6", label="5th-95th pct")
    ax.fill_between(years_axis, p25, p75, alpha=BAND_ALPHA_INNER, color="#3b82f6", label="25th-75th pct")
    ax.plot(years_axis, p50, color="#1d4ed8", linewidth=2, label="Median")
    ax.plot(years_axis, output.result.invested_capital, color="#6b7280", linestyle="--", linewidth=1.5,
            label="Invested capital")

    ax.set_title("Portfolio Growth - Simulated Outcomes")
    ax.set_xlabel("Year")
    ax.set_ylabel(f"Portfolio Value ({currency})")
    ax.yaxis.set_major_formatter(lambda x, pos: format_currency(x, currency))
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def histogram_chart(output: EngineOutput, currency: str = "USD", target_value: float | None = None) -> Figure:
    """Distribution of final portfolio values with key percentile markers."""
    final_values = output.result.portfolio_value[:, -1]

    fig = Figure(figsize=(7.5, 4.8), dpi=100)
    ax = fig.add_subplot(111)
    ax.hist(final_values, bins=60, color="#10b981", alpha=0.75, edgecolor="white", linewidth=0.3)

    for p, label, style in [(5, "P5", ":"), (50, "Median", "-"), (95, "P95", ":")]:
        val = output.stats.percentiles[p] if p in output.stats.percentiles else np.percentile(final_values, p)
        ax.axvline(val, color="#111827", linestyle=style, linewidth=1.2)
        ax.text(val, ax.get_ylim()[1] * 0.95, label, rotation=90, va="top", ha="right", fontsize=8)

    if target_value is not None:
        ax.axvline(target_value, color="#dc2626", linewidth=1.5, label=f"Target: {format_currency(target_value, currency)}")
        ax.legend(fontsize=8)

    ax.set_title(f"Distribution of Final Portfolio Values (Year {output.result.years})")
    ax.set_xlabel(f"Portfolio Value ({currency})")
    ax.set_ylabel("Number of Simulations")
    ax.xaxis.set_major_formatter(lambda x, pos: format_currency(x, currency))
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    return fig


def drawdown_chart(output: EngineOutput, currency: str = "USD") -> Figure:
    """Median and worst-case (95th percentile) drawdown over time."""
    dd = output.drawdown  # (n_sims, years+1)
    years_axis = np.arange(dd.shape[1])
    median_dd = np.percentile(dd, 50, axis=0)
    p95_dd = np.percentile(dd, 95, axis=0)  # worse drawdowns are higher values

    fig = Figure(figsize=(7.5, 4.2), dpi=100)
    ax = fig.add_subplot(111)
    ax.fill_between(years_axis, 0, -p95_dd * 100, color="#ef4444", alpha=0.25, label="95th pct (worse case) drawdown")
    ax.plot(years_axis, -median_dd * 100, color="#b91c1c", linewidth=2, label="Median drawdown")

    ax.set_title("Drawdown From Peak Over Time")
    ax.set_xlabel("Year")
    ax.set_ylabel("Drawdown (%)")
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def contribution_vs_value_chart(output: EngineOutput, currency: str = "USD") -> Figure:
    """Cumulative invested capital vs. median portfolio value, profit shaded."""
    pv_median = np.percentile(output.result.portfolio_value, 50, axis=0)
    invested = output.result.invested_capital
    years_axis = np.arange(len(invested))

    fig = Figure(figsize=(7.5, 4.2), dpi=100)
    ax = fig.add_subplot(111)
    ax.plot(years_axis, invested, color="#6b7280", linewidth=1.8, label="Invested Capital")
    ax.plot(years_axis, pv_median, color="#1d4ed8", linewidth=2, label="Median Portfolio Value")
    ax.fill_between(years_axis, invested, pv_median, where=(pv_median >= invested),
                     color="#22c55e", alpha=0.25, interpolate=True, label="Profit")
    ax.fill_between(years_axis, invested, pv_median, where=(pv_median < invested),
                     color="#ef4444", alpha=0.25, interpolate=True)

    ax.set_title("Invested Capital vs. Median Portfolio Value")
    ax.set_xlabel("Year")
    ax.set_ylabel(f"Value ({currency})")
    ax.yaxis.set_major_formatter(lambda x, pos: format_currency(x, currency))
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig
