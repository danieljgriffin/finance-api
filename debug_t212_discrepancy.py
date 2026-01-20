import asyncio
import sys
import os
import logging
from datetime import datetime
import yfinance as yf

# Add the parent directory to sys.path
sys.path.append(os.getcwd())

from app.utils.price_fetcher import PriceFetcher

# Configure logging
logging.basicConfig(level=logging.INFO)

async def check_discrepancy():
    fetcher = PriceFetcher()
    
    print(f"\n--- FX Rate Investigation ---")
    
    tickers = ['GBPUSD=X', 'USDGBP=X', 'GBP=X']
    
    for t in tickers:
        try:
            ticker = yf.Ticker(t)
            hist = ticker.history(period='1d')
            close = hist['Close'].iloc[-1] if not hist.empty else None
            
            try:
                fast = ticker.fast_info.last_price
            except:
                fast = None
                
            print(f"Ticker: {t}")
            print(f"  History Close: {close}")
            print(f"  Fast Info: {fast}")
             
        except Exception as e:
            print(f"{t}: Error {e}")
            
    # 2. Check Stocks
    symbols = ['TSLA', 'NVDA', 'META', 'PLTR']
    print(f"\n--- Stock Prices (Source: Yahoo) ---")
    
    # Holdings from user screenshot (approx)
    holdings = {
        'TSLA': 7.019,
        'NVDA': 10.251,
        'META': 2.123,
        'PLTR': 2.624
    }
    
    total_app_value = 0
    
    for sym in symbols:
        # Fetch raw price (USD usually)
        price_gbp = await fetcher.get_price_async(sym)
        
        # We want to see the underlying USD price too to compare
        ticker = yf.Ticker(sym)
        try:
             raw_price = ticker.fast_info.last_price
             
             # Check extended fields
             info = ticker.info
             current = info.get('currentPrice')
             bid = info.get('bid')
             ask = info.get('ask')
             pre = info.get('preMarketPrice')
             
             print(f"{sym}:")
             print(f"  Fast Last: {raw_price}")
             print(f"  Info Current: {current}")
             print(f"  Bid: {bid} | Ask: {ask}")
             print(f"  PreMarket: {pre}")
             print(f"  Converted GBP (Current Logic): {price_gbp:.2f}")
             
             if sym in holdings:
                 val = price_gbp * holdings[sym]
                 total_app_value += val
                 # print(f"  -> Value for {holdings[sym]} shares: £{val:.2f}")
                 
        except Exception as e:
            print(f"{sym}: Error {e}")
            
    print(f"\nTotal Calculated Value: £{total_app_value:.2f}")
    print(f"User Reported T212 Value: £2229.00")
    print(f"Diff: £{total_app_value - 2229:.2f}")

if __name__ == "__main__":
    asyncio.run(check_discrepancy())
