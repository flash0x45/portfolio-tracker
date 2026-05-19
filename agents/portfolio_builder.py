import logging
from typing import Dict, Iterable, Optional

import requests

from config import FUND_SLUG

SCHEME_URL = "https://groww.in/v1/api/data/mf/web/v4/scheme/search/{slug}"
COMPANY_URL = "https://groww.in/v1/api/stocks_data/v1/company/search_id/{search_id}"


def build_portfolio(slug: str = FUND_SLUG) -> Dict[str, float]:
    holdings = _fetch_holdings(slug)
    portfolio: Dict[str, float] = {}
    symbol_cache: Dict[str, Optional[str]] = {}

    for holding in holdings:
        if not _is_equity(holding):
            continue

        search_id = _get_search_id(holding)
        if not search_id:
            logging.warning("Missing stock_search_id for holding: %s", _holding_name(holding))
            continue

        if search_id in symbol_cache:
            symbol = symbol_cache[search_id]
        else:
            symbol = _fetch_symbol(search_id)
            symbol_cache[search_id] = symbol

        if not symbol:
            logging.warning("Unable to resolve NSE symbol for search_id %s", search_id)
            continue

        weight = _get_weight(holding)
        if weight is None:
            logging.warning("Missing corpus_per for holding: %s", _holding_name(holding))
            continue

        portfolio[f"{symbol}.NS"] = float(weight)

    total_weight = sum(portfolio.values())
    if total_weight == 0:
        logging.warning("Portfolio weights sum to 0. Check the Groww response.")
    elif not (95 <= total_weight <= 105):
        logging.warning("Total equity weight %.2f%% is far from 100%%", total_weight)
    else:
        logging.info("Total equity weight %.2f%%", total_weight)

    return portfolio


def _fetch_holdings(slug: str) -> Iterable[dict]:
    url = SCHEME_URL.format(slug=slug)
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    holdings = _extract_holdings(payload)
    if not holdings:
        raise ValueError("No holdings found in Groww response.")
    return holdings


def _extract_holdings(payload: object) -> Iterable[dict]:
    if isinstance(payload, dict):
        for key in ("holdings", "fund_holdings"):
            if isinstance(payload.get(key), list):
                return payload[key]
        for section_key in ("scheme", "data"):
            section = payload.get(section_key)
            if isinstance(section, dict):
                for key in ("holdings", "fund_holdings"):
                    if isinstance(section.get(key), list):
                        return section[key]
    return []


def _is_equity(holding: dict) -> bool:
    name = holding.get("instrument_name") or holding.get("instrumentName")
    return isinstance(name, str) and name.strip().lower() == "equity"


def _get_search_id(holding: dict) -> Optional[str]:
    for key in ("stock_search_id", "stockSearchId", "search_id", "searchId"):
        value = holding.get(key)
        if value:
            return str(value)
    return None


def _get_weight(holding: dict) -> Optional[float]:
    for key in ("corpus_per", "corpusPer", "corpusPercentage"):
        value = holding.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def _fetch_symbol(search_id: str) -> Optional[str]:
    url = COMPANY_URL.format(search_id=search_id)
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    symbol = _extract_symbol(payload)
    if not symbol:
        return None
    normalized = symbol.strip().upper()
    if normalized.endswith(".NS"):
        normalized = normalized[:-3]
    return normalized or None


def _extract_symbol(payload: object) -> Optional[str]:
    if isinstance(payload, dict):
        for key in ("nseScriptCode", "nseSymbol", "nse_script_code"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        for section_key in ("company", "data", "header"):
            section = payload.get(section_key)
            if isinstance(section, dict):
                for key in ("nseScriptCode", "nseSymbol", "nse_script_code"):
                    value = section.get(key)
                    if isinstance(value, str) and value.strip():
                        return value
    return None


def _holding_name(holding: dict) -> str:
    for key in ("company_name", "companyName", "name"):
        value = holding.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return "unknown"
