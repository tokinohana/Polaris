# 🌟 Polaris: Monte Carlo Portfolio Simulator
### v1 – Core

> A desktop application for probabilistic portfolio analysis using **Monte Carlo simulation**, **correlated asset modeling**, and **dynamic DCA schedules**.

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![Status](https://img.shields.io/badge/Status-v1%20Core-success)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

Monte Carlo Portfolio Simulator is a desktop application built with **Python**, **Tkinter**, and **NumPy** that models thousands of possible future portfolio outcomes instead of producing a single deterministic forecast.

The simulator supports:

- Correlated multi-asset portfolios
- Bitcoin / crypto regime modeling
- Dynamic Dollar-Cost Averaging (DCA)
- Portfolio rebalancing
- Interactive charts
- Statistical probability analysis

Instead of answering:

> "How much will my portfolio be worth?"

the simulator answers:

> "Given these assumptions, what range of outcomes is statistically plausible?"

---

## Current Scope (v1)

### Included

- Portfolio Builder
- Correlated Monte Carlo Engine
- Variable DCA
- Portfolio Rebalancing
- Statistical Summary
- CSV Export
- Fan Chart
- Histogram
- Drawdown Chart
- Invested Capital vs Portfolio Value

### Planned

- Black Swan Event Engine
- Inflation
- Taxes & Fees
- Sensitivity Analysis
- Scenario Explorer
- Historical Backtesting
- Portfolio Optimization
- PDF Reports

---

## Installation

```bash
pip install -r requirements.txt
python main.py
```

Python **3.12+** is recommended.

Linux users may need:

```bash
sudo apt install python3-tk
```

---

# Default Preset

The application ships with a sample portfolio:

| Asset | Role |
|--------|------|
| Bitcoin | Core Growth |
| Solana | Satellite / Moonshot |
| SPY | Market Anchor |
| Microsoft | Quality Growth |
| NVIDIA | AI Growth |

> **Important**
>
> Prices, holdings, and DCA values are placeholders.
> Update them to match your own brokerage or exchange before using the simulator.

---

# Project Architecture

```text
main.py
│
├── gui/
│   ├── app_state.py
│   ├── portfolio_tab.py
│   ├── assumptions_tab.py
│   ├── simulation_tab.py
│   └── charts_tab.py
│
├── simulation/
│   ├── asset.py
│   ├── portfolio.py
│   ├── montecarlo.py
│   ├── statistics.py
│   ├── engine.py
│   └── presets.py
│
├── charts/
│   └── charts.py
│
├── utils/
│   └── helpers.py
│
└── data/
    └── presets.json
```

The project follows a layered architecture:

```
GUI
    ↓
Simulation Engine
    ↓
Statistics
    ↓
Charts
```

The simulation engine is completely independent of the GUI, making it reusable for notebooks, CLI tools, or unit tests.

---

# Simulation Engine

<details>

<summary><strong>Correlation Model</strong></summary>

Assets are correlated using a Cholesky decomposition of the user-defined correlation matrix.

If the matrix is not mathematically valid (not positive semi-definite), it is automatically repaired before simulation.

</details>

<details>

<summary><strong>Return Models</strong></summary>

### Lognormal

Designed for:

- ETFs
- Broad market indices
- Mature stocks

Inputs:

- Expected annual return
- Annual volatility

---

### Regime Model

Designed for:

- Bitcoin
- Solana
- High-volatility assets

Each regime defines:

- Probability
- Expected return
- Volatility

Example:

| Regime | Probability | Return |
|---------|------------:|-------:|
| Bear | 20% | -20% |
| Base | 55% | +35% |
| Bull | 25% | +80% |

</details>

<details>

<summary><strong>Contribution Model</strong></summary>

Each asset supports:

- Weekly DCA
- Monthly DCA
- Annual DCA Growth
- Per-Year Overrides

Contributions are applied after annual returns.

</details>

<details>

<summary><strong>Rebalancing</strong></summary>

Supported strategies:

- Never
- Annual

Annual rebalancing restores the portfolio to its target allocation.

</details>

---

# Statistics

The simulator reports:

| Metric |
|---------|
| Mean |
| Median |
| Minimum |
| Maximum |
| Standard Deviation |
| Percentiles (5–95%) |
| Probability of Profit |
| Probability Above Target |
| Probability Below Target |
| Median CAGR |
| Worst Year |
| Best Year |
| Drawdown |

---

# Charts

The application generates four core visualizations.

| Chart | Description |
|--------|-------------|
| Fan Chart | Portfolio uncertainty bands over time |
| Histogram | Distribution of ending portfolio values |
| Drawdown | Median and worst-case drawdown |
| Invested Capital | Invested capital vs portfolio value |

All charts include the standard Matplotlib toolbar for zooming, panning, and PNG export.

---

# CSV Export

Simulation results can be exported as CSV.

Included:

- Percentile bands
- Invested capital
- Drawdown
- Summary statistics

---

# Roadmap

## v2

- Monthly simulation timestep
- Global market regimes
- Black Swan Event Engine
- Inflation
- Taxes
- FX Modeling

## v3

- Scenario Explorer
- Sensitivity Analysis
- Historical Backtesting
- Efficient Frontier
- Portfolio Optimization

---

# Disclaimer

This software is intended for educational and planning purposes.

The simulator does **not** predict future market performance.

All results depend entirely on the assumptions supplied by the user. Probability distributions represent simulated outcomes under those assumptions—not forecasts or investment advice.