"""
simulation/presets.py

Converts between the JSON preset/save format and the Portfolio/Asset
dataclasses. Kept separate from portfolio.py so the dataclasses stay free
of I/O concerns.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from simulation.asset import Asset, AssetClass, Regime, ReturnModelType
from simulation.portfolio import Portfolio, RebalanceFrequency

DEFAULT_PRESETS_PATH = Path(__file__).resolve().parent.parent / "data" / "presets.json"


def _asset_from_dict(d: dict) -> Asset:
    regimes = [Regime(**r) for r in d.get("regimes", [])]
    return Asset(
        name=d["name"],
        symbol=d["symbol"],
        asset_class=AssetClass(d.get("asset_class", "Custom")),
        allocation_pct=d.get("allocation_pct", 0.0),
        initial_price=d.get("initial_price", 1.0),
        current_price=d.get("current_price", 1.0),
        starting_holdings=d.get("starting_holdings", 0.0),
        weekly_dca=d.get("weekly_dca", 0.0),
        monthly_dca=d.get("monthly_dca", 0.0),
        annual_dca_increase_pct=d.get("annual_dca_increase_pct", 0.0),
        dca_overrides={int(k): v for k, v in d.get("dca_overrides", {}).items()},
        return_model=ReturnModelType(d.get("return_model", "lognormal")),
        expected_return=d.get("expected_return", 0.08),
        volatility=d.get("volatility", 0.15),
        regimes=regimes,
    )


def _asset_to_dict(a: Asset) -> dict:
    return {
        "name": a.name,
        "symbol": a.symbol,
        "asset_class": a.asset_class.value,
        "allocation_pct": a.allocation_pct,
        "initial_price": a.initial_price,
        "current_price": a.current_price,
        "starting_holdings": a.starting_holdings,
        "weekly_dca": a.weekly_dca,
        "monthly_dca": a.monthly_dca,
        "annual_dca_increase_pct": a.annual_dca_increase_pct,
        "dca_overrides": {str(k): v for k, v in a.dca_overrides.items()},
        "return_model": a.return_model.value,
        "expected_return": a.expected_return,
        "volatility": a.volatility,
        "regimes": [r.__dict__ for r in a.regimes],
    }


def portfolio_from_dict(d: dict) -> Portfolio:
    assets = [_asset_from_dict(a) for a in d["assets"]]
    corr_block = d.get("correlation")
    correlation = None
    if corr_block:
        correlation = np.array(corr_block["matrix"], dtype=float)
    portfolio = Portfolio(
        name=d.get("name", "Portfolio"),
        currency=d.get("currency", "USD"),
        assets=assets,
        correlation=correlation,
        rebalance_frequency=RebalanceFrequency(d.get("rebalance_frequency", "Never")),
    )
    return portfolio


def portfolio_to_dict(p: Portfolio) -> dict:
    return {
        "name": p.name,
        "currency": p.currency,
        "rebalance_frequency": p.rebalance_frequency.value,
        "assets": [_asset_to_dict(a) for a in p.assets],
        "correlation": {
            "order": p.asset_names(),
            "matrix": p.correlation.tolist(),
        },
    }


def load_presets(path: Path | str = DEFAULT_PRESETS_PATH) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("presets", [])


def load_default_portfolio(path: Path | str = DEFAULT_PRESETS_PATH) -> Portfolio:
    presets = load_presets(path)
    if not presets:
        return Portfolio(name="New Portfolio", assets=[])
    return portfolio_from_dict(presets[0]["portfolio"])


def save_portfolio(portfolio: Portfolio, path: Path | str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(portfolio_to_dict(portfolio), f, indent=2)


def load_portfolio(path: Path | str) -> Portfolio:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return portfolio_from_dict(data)
