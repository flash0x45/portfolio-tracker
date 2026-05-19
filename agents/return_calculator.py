from typing import Dict, List

import pandas as pd


def calculate_returns(
    portfolio: Dict[str, float],
    prices: Dict[str, float],
    prev_close: Dict[str, float],
) -> Dict[str, object]:
    per_stock_returns: Dict[str, float] = {}
    excluded: List[str] = []
    valid_weights: Dict[str, float] = {}

    for symbol, weight_pct in portfolio.items():
        price = prices.get(symbol)
        previous = prev_close.get(symbol)

        if price is None or previous is None or pd.isna(price) or pd.isna(previous):
            excluded.append(symbol)
            continue

        if previous <= 0:
            excluded.append(symbol)
            continue

        return_pct = (price - previous) / previous * 100
        per_stock_returns[symbol] = round(return_pct, 2)
        valid_weights[symbol] = weight_pct

    total_weight = sum(valid_weights.values())
    portfolio_return = 0.0
    if total_weight > 0:
        for symbol, return_pct in per_stock_returns.items():
            weight_decimal = valid_weights[symbol] / total_weight
            portfolio_return += weight_decimal * return_pct

    return {
        "per_stock_returns": per_stock_returns,
        "portfolio_return": round(portfolio_return, 2),
        "excluded_symbols": excluded,
    }
