import asyncio
from app.utils.price_fetcher import PriceFetcher

async def test():
    pf = PriceFetcher()
    symbols = ['VUAG.L', 'XDEW.L', 'RR.L']
    
    print("\n--- DEBUGGING PRICES ---")
    for s in symbols:
        print(f"\nSymbol: {s}")
        
        # 1. Try Yahoo (Standard)
        # We can't easily force it to fail to test Google here without mocking, 
        # but we can call the scraper directly.
        
        # Test 1: Full get_price logic
        final = pf.get_price(s)
        print(f"  > get_price() Final Result: {final}")
        
        # Test 2: Explicit Google Scrape (Raw)
        google_raw = pf.scrape_google_finance(s)
        print(f"  > Google Raw Scrape: {google_raw}")

if __name__ == "__main__":
    asyncio.run(test())
