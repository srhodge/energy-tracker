import yfinance as yf

tickers = ["CNQ", "STO.AX", "FRO", "ENB", "SDRL", "NBR", "WDS", "PBR", "BPT.AX", "TGS",
           "ARC", "CVE", "HAL", "BTE", "ARX.TO", "GLNG", "DHT", "NAT", "ALD.AX", "OMV.F"]

for t in tickers:
    info = yf.Ticker(t).info
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    name = info.get("shortName", "?")
    print(f"{t:<12} {name:<35} sector={sector:<30} industry={industry}")
