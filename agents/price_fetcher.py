import logging
import time
from typing import Dict, List, Optional

import pandas as pd
import requests
import yfinance as yf

from config import (
    MAX_FETCH_RETRIES,
    RETRY_BACKOFF_S,
    YFINANCE_DAILY_INTERVAL,
    YFINANCE_INTRADAY_INTERVAL,
)
from agents.market_clock import now_ist


def fetch_prices(symbols: List[str]) -> Optional[Dict[str, object]]:
    if not symbols:
        return None

    for attempt in range(1, MAX_FETCH_RETRIES + 1):
        try:
            intraday = _download_intraday(symbols)
            daily = _download_daily(symbols)
            if intraday is None or intraday.empty or daily is None or daily.empty:
                raise ValueError("Empty data from yfinance")

            prices = _extract_latest_close(intraday, symbols)
            prev_close = _extract_prev_close(daily, symbols)
            _log_missing(symbols, prices, prev_close)

            return {
                "timestamp": now_ist().isoformat(),
                "prices": prices,
                "prev_close": prev_close,
            }
        except (
            ValueError,
            KeyError,
            IndexError,
            pd.errors.EmptyDataError,
            requests.exceptions.RequestException,
        ) as exc:
            logging.warning("Price fetch attempt %d failed: %s", attempt, exc)

        if attempt < MAX_FETCH_RETRIES:
            time.sleep(RETRY_BACKOFF_S)

    return None


def _download_intraday(symbols: List[str]) -> pd.DataFrame:
    tickers = " ".join(symbols)
    return yf.download(
        tickers=tickers,
        period="1d",
        interval=YFINANCE_INTRADAY_INTERVAL,
        group_by="ticker",
        threads=True,
        progress=False,
    )


def _download_daily(symbols: List[str]) -> pd.DataFrame:
    tickers = " ".join(symbols)
    return yf.download(
        tickers=tickers,
        period="2d",
        interval=YFINANCE_DAILY_INTERVAL,
        group_by="ticker",
        threads=True,
        progress=False,
    )


def _extract_latest_close(
    intraday: pd.DataFrame, symbols: List[str]
) -> Dict[str, float]:
    prices: Dict[str, float] = {}
    if len(symbols) == 1:
        close_series = intraday.get("Close")
        if isinstance(close_series, pd.Series):
            close_series = close_series.dropna()
            if not close_series.empty:
                prices[symbols[0]] = float(close_series.iloc[-1])
        return prices

    if isinstance(intraday.columns, pd.MultiIndex):
        for symbol in symbols:
            if symbol in intraday.columns.get_level_values(0):
                close_series = intraday[symbol].get("Close")
            elif symbol in intraday.columns.get_level_values(1):
                close_series = intraday.xs(symbol, level=1, axis=1).get("Close")
            else:
                close_series = None

            if isinstance(close_series, pd.Series):
                close_series = close_series.dropna()
                if not close_series.empty:
                    prices[symbol] = float(close_series.iloc[-1])
    return prices


def _extract_prev_close(
    daily: pd.DataFrame, symbols: List[str]
) -> Dict[str, float]:
    prev_close: Dict[str, float] = {}
    if len(symbols) == 1:
        close_series = daily.get("Close")
        if isinstance(close_series, pd.Series):
            close_series = close_series.dropna()
            if not close_series.empty:
                index = -2 if len(close_series) >= 2 else -1
                prev_close[symbols[0]] = float(close_series.iloc[index])
        return prev_close

    if isinstance(daily.columns, pd.MultiIndex):
        for symbol in symbols:
            if symbol in daily.columns.get_level_values(0):
                close_series = daily[symbol].get("Close")
            elif symbol in daily.columns.get_level_values(1):
                close_series = daily.xs(symbol, level=1, axis=1).get("Close")
            else:
                close_series = None

            if isinstance(close_series, pd.Series):
                close_series = close_series.dropna()
                if not close_series.empty:
                    index = -2 if len(close_series) >= 2 else -1
                    prev_close[symbol] = float(close_series.iloc[index])
    return prev_close


def _log_missing(
    symbols: List[str],
    prices: Dict[str, float],
    prev_close: Dict[str, float],
) -> None:
    missing_prices = [symbol for symbol in symbols if symbol not in prices]
    missing_prev = [symbol for symbol in symbols if symbol not in prev_close]

    if missing_prices:
        logging.warning("Missing intraday prices for: %s", ", ".join(missing_prices))
    if missing_prev:
        logging.warning("Missing previous close for: %s", ", ".join(missing_prev))
