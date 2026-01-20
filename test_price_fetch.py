import asyncio
import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.getcwd())

from app.utils.price_fetcher import PriceFetcher

async def test_fetch():
    fetcher = PriceFetcher()
    symbols = ['META', 'VUSA.L', 'GSK.L', 'SGLN.L', 'NVDA', 'RR.L']
    
    print(f"Testing fetch for: {symbols}")
    
    # Test sync fetch
    print("\n--- Sync Fetch Test ---")
    for sym in symbols:
        try:
            price = fetcher.get_price(sym)
            print(f"{sym}: {price}")
        except Exception as e:
            print(f"{sym}: FAILED ({e})")
            
    # Test async fetch
    print("\n--- Async Fetch Test ---")
    try:
        prices = await fetcher.get_multiple_prices_async(symbols)
        print(f"Async Results: {prices}")
    except Exception as e:
        print(f"Async Batch Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_fetch())
