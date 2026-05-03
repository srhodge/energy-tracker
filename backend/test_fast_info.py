import yfinance as yf
import time

tickers = ["CNQ", "ENB", "CVE", "HAL"]

for t in tickers:
    try:
        fi = yf.Ticker(t).fast_info
        price = getattr(fi, "last_price", "N/A")
        mcap = getattr(fi, "market_cap", "N/A")
        print(f"{t}: price={price}, mcap={mcap}")
    except Exception as e:
        print(f"{t}: ERROR {e}")
    time.sleep(1)
