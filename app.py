import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from agents.market_clock import get_market_status
from agents.portfolio_builder import build_portfolio
from agents.price_fetcher import fetch_prices
from agents.return_calculator import calculate_returns
from config import FUND_SLUG, POLL_INTERVAL_S

st.set_page_config(page_title="Portfolio Tracker", layout="wide")
st.title("Real-Time Portfolio Tracker")

st.sidebar.header("Settings")
slug = st.sidebar.text_input("Fund slug", FUND_SLUG)
refresh_interval = st.sidebar.number_input(
    "Refresh interval (seconds)",
    min_value=10,
    max_value=600,
    value=POLL_INTERVAL_S,
    step=10,
)

st_autorefresh(interval=int(refresh_interval * 1000), key="refresh")


@st.cache_data(ttl=24 * 60 * 60)
def load_portfolio(fund_slug: str) -> dict[str, float]:
    return build_portfolio(fund_slug)


portfolio = load_portfolio(slug)
if not portfolio:
    st.error("No portfolio holdings resolved. Check the fund slug or Groww API.")
    st.stop()

is_open, reason, next_open = get_market_status()

status_message = "Market is open." if is_open else f"Market closed: {reason}."
if next_open is not None:
    status_message = f"{status_message} Next open: {next_open.strftime('%Y-%m-%d %H:%M %Z')}."

st.info(status_message)

data = None
returns = None
if is_open:
    data = fetch_prices(list(portfolio.keys()))
    if data is None:
        st.warning("Price fetch failed. Refresh to retry.")
    else:
        returns = calculate_returns(portfolio, data["prices"], data["prev_close"])

col1, col2, col3 = st.columns(3)
col1.metric(
    "Portfolio Return",
    f"{returns['portfolio_return']:.2f}%" if returns else "--",
)
col2.metric("Symbols", f"{len(portfolio)}")
col3.metric("Excluded", f"{len(returns['excluded_symbols'])}" if returns else "0")

if data:
    st.caption(f"Last updated: {data['timestamp']}")

rows = []
prices = data["prices"] if data else {}
prev_close = data["prev_close"] if data else {}
per_stock = returns["per_stock_returns"] if returns else {}

for symbol, weight in portfolio.items():
    rows.append(
        {
            "Symbol": symbol,
            "Weight %": weight,
            "Price": prices.get(symbol),
            "Prev Close": prev_close.get(symbol),
            "Return %": per_stock.get(symbol),
        }
    )

table = pd.DataFrame(rows)
table["Weight %"] = table["Weight %"].round(2)
table["Price"] = pd.to_numeric(table["Price"], errors="coerce").round(2)
table["Prev Close"] = pd.to_numeric(table["Prev Close"], errors="coerce").round(2)
table["Return %"] = pd.to_numeric(table["Return %"], errors="coerce").round(2)
table = table.sort_values("Weight %", ascending=False)

def _color_return(value: float) -> str:
    if pd.isna(value):
        return ""
    if value > 0:
        return "color: #0f9d58"
    if value < 0:
        return "color: #db4437"
    return "color: #999999"


styler = table.style.format(
    {
        "Weight %": "{:.2f}",
        "Price": "{:.2f}",
        "Prev Close": "{:.2f}",
        "Return %": "{:.2f}",
    },
    na_rep="--",
)
if hasattr(styler, "map"):
    styled_table = styler.map(_color_return, subset=["Return %"])
else:
    styled_table = styler.applymap(_color_return, subset=["Return %"])
st.dataframe(styled_table, use_container_width=True)

if returns and returns["excluded_symbols"]:
    st.warning("Excluded symbols: " + ", ".join(returns["excluded_symbols"]))
