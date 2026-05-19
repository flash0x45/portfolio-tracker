# Real-Time Portfolio Tracker

Fetches equity holdings for a Groww mutual fund scheme, resolves NSE symbols,
and tracks live price movements during Indian market hours.

## Setup

1. Create a virtual environment (optional) and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Adjust settings in `config.py` if needed:
   - Fund slug
   - Poll interval
   - NSE holidays list

## Run

```bash
python main.py
```

### Streamlit UI

```bash
streamlit run streamlit_app.py
```

The tracker only runs during NSE market hours (09:15-15:30 IST). Outside those
hours it will log the reason and exit or wait until the market opens.
