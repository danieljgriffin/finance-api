from app.utils.price_fetcher import PriceFetcher
from app.database import SessionLocal
from app.services.holdings_service import HoldingsService
from app.models import Investment
import asyncio

async def debug_pricing_and_balance():
    db = SessionLocal()
    
    print("--- 1. Check Investments ---")
    investments = db.query(Investment).filter(Investment.symbol == "BTC").all()
    for inv in investments:
        print(f"ID: {inv.id}, Name: {inv.name}, Symbol: {inv.symbol}, Holdings: {inv.holdings}, Price: {inv.current_price}")
        if inv.holdings == 0:
            print("  [WARNING] Holdings are 0. Sync might have failed or wallet is empty.")
    
    print("\n--- 2. Test PriceFetcher for BTC ---")
    fetcher = PriceFetcher()
    price = await fetcher.get_price_async("BTC")
    print(f"Fetched Price for BTC: {price}")
    
    if price:
        print("  [SUCCESS] Price fetching works.")
    else:
        print("  [FAILURE] Price fetching returned None.")

    db.close()

if __name__ == "__main__":
    asyncio.run(debug_pricing_and_balance())
