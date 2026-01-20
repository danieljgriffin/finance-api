import yfinance as yf
import pandas as pd

def check_intraday():
    print("Checking intraday headers for GBPUSD=X...")
    # Try to get 1 minute data for the last 5 days to see the timestamp of the latest data point
    df = yf.download("GBPUSD=X", period="5d", interval="1m", progress=False)
    
    if not df.empty:
        last = df.iloc[-1]
        print(f"Latest Data Point:\n{last}")
        print(f"Time: {last.name}")
    else:
        print("No intraday data found.")

if __name__ == "__main__":
    check_intraday()
