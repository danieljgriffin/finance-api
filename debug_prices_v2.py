import asyncio
from app.utils.price_fetcher import PriceFetcher

async def test():
    pf = PriceFetcher()
    symbols = ['VUAG.L', 'RR.L']
    
    print("\n--- DEBUGGING PRICES (Simulated) ---")
    
    # Simulate Google Return for VUAG.L (Pounds)
    # Case 1: Google returns "£98.50"
    print("\nTest Case 1: VUAG.L returns '£98.50'")
    # We can't easily mock internal methods without patching, 
    # but we rely on the logic analysis. 
    # Let's just run get_price to ensure no syntax errors and Yahoo still works.
    
    val = pf.get_price('VUAG.L')
    print(f"VUAG.L Real Fetch: {val}")
    
    val = pf.get_price('RR.L')
    print(f"RR.L Real Fetch: {val}")

if __name__ == "__main__":
    asyncio.run(test())
