import asyncio
from app.utils.price_fetcher import PriceFetcher
import yfinance as yf

async def test():
    pf = PriceFetcher()
    symbol = 'SOL'
    
    print(f"\n--- DEBUGGING {symbol} ---")
    
    # 1. Test CoinGecko Direct
    print("1. Testing CoinGecko...")
    cg_price = pf.get_crypto_price_from_coingecko(symbol)
    print(f"   > CoinGecko Result: {cg_price}")
    
    # 2. Test Yahoo Direct (Raw 'SOL')
    print("\n2. Testing Yahoo ('SOL')...")
    try:
        ticker = yf.Ticker(symbol)
        curr = ticker.fast_info.currency
        price = ticker.fast_info.last_price
        print(f"   > Yahoo 'SOL': {price} {curr}")
    except Exception as e:
        print(f"   > Yahoo Failed: {e}")

    # 3. Test Yahoo Direct ('SOL-USD')
    print("\n3. Testing Yahoo ('SOL-USD')...")
    try:
        ticker = yf.Ticker('SOL-USD')
        curr = ticker.fast_info.currency
        price = ticker.fast_info.last_price
        print(f"   > Yahoo 'SOL-USD': {price} {curr}")
    except Exception as e:
        print(f"   > Yahoo 'SOL-USD' Failed: {e}")

    # 4. Test Google Fallback
    print("\n4. Testing Google 'SOL'...")
    try:
        res = pf.scrape_google_finance(symbol)
        print(f"   > Google 'SOL': {res}")
    except Exception as e:
        print(f"   > Google Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
