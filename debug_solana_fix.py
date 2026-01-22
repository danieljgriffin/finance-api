import asyncio
from app.utils.price_fetcher import PriceFetcher

async def test():
    pf = PriceFetcher()
    symbol = 'SOL'
    
    print(f"\n--- VERIFYING FIX FOR {symbol} ---")
    
    # This should now return ~127 USD (converted to GBP ~94)
    # properly falling back to SOL-USD on Yahoo/Google
    try:
        price = pf.get_price(symbol)
        print(f"get_price('SOL') Result: {price}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
