import logging
import time
from typing import Dict

from agents.market_clock import get_market_status, now_ist
from agents.portfolio_builder import build_portfolio
from agents.price_fetcher import fetch_prices
from agents.return_calculator import calculate_returns
from config import FUND_SLUG, POLL_INTERVAL_S


def run() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    portfolio = build_portfolio(FUND_SLUG)
    if not portfolio:
        logging.error("No portfolio holdings resolved. Exiting.")
        return

    portfolio_date = now_ist().date()
    _log_portfolio_stats(portfolio, "Portfolio loaded")

    try:
        while True:
            if not _handle_market_state():
                return

            current = now_ist()
            if current.date() != portfolio_date:
                portfolio = build_portfolio(FUND_SLUG)
                portfolio_date = current.date()
                _log_portfolio_stats(portfolio, "Portfolio refreshed")

            data = fetch_prices(list(portfolio.keys()))
            if data is None:
                logging.warning("Skipping cycle due to price fetch failure.")
                time.sleep(POLL_INTERVAL_S)
                continue

            returns = calculate_returns(
                portfolio, data["prices"], data["prev_close"]
            )
            _print_returns(data["timestamp"], portfolio, returns)

            time.sleep(POLL_INTERVAL_S)
    except KeyboardInterrupt:
        logging.info("Received interrupt. Exiting.")


def _handle_market_state() -> bool:
    is_open, reason, next_open = get_market_status()
    if is_open:
        return True

    if next_open is None:
        logging.info("Market closed: %s. Exiting.", reason)
        return False

    now = now_ist()
    if next_open.date() == now.date() and next_open > now:
        wait_seconds = (next_open - now).total_seconds()
        logging.info(
            "Market closed: %s. Waiting %.0f seconds until open.",
            reason,
            wait_seconds,
        )
        time.sleep(max(wait_seconds, 0))
        return True

    logging.info("Market closed: %s. Exiting.", reason)
    return False


def _print_returns(
    timestamp: str,
    portfolio: Dict[str, float],
    returns: Dict[str, object],
) -> None:
    per_stock = returns["per_stock_returns"]
    excluded = returns["excluded_symbols"]

    print(f"[{timestamp}] Live Returns:")
    for symbol in sorted(per_stock.keys(), key=lambda s: portfolio.get(s, 0), reverse=True):
        weight = portfolio.get(symbol, 0.0)
        return_pct = per_stock[symbol]
        print(f"{symbol:<15} {return_pct:>7.2f}% (wt: {weight:.2f}%)")

    if excluded:
        print(f"Excluded symbols: {', '.join(excluded)}")

    print(f"Portfolio Return: {returns['portfolio_return']:.2f}%")
    print("-" * 60)


def _log_portfolio_stats(portfolio: Dict[str, float], label: str) -> None:
    total_weight = sum(portfolio.values())
    logging.info(
        "%s: %d symbols | Total weight %.2f%%",
        label,
        len(portfolio),
        total_weight,
    )
