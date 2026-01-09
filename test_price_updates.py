
import asyncio
from app.database import SessionLocal
from app.services.holdings_service import HoldingsService
from app.models import Investment
from app.utils.price_fetcher import PriceFetcher
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_updates():
    db = SessionLocal()
    try:
        holdings_service = HoldingsService(db, user_id=1)
        price_fetcher = PriceFetcher()

        print("--- Fetching all investments ---")
        investments = db.query(Investment).filter(Investment.user_id == 1).all()
        
        symbols = [inv.symbol for inv in investments if inv.symbol]
        unique_symbols = list(set(symbols))
        
        print(f"Found {len(investments)} investments with {len(unique_symbols)} unique symbols.")
        print(f"Symbols: {unique_symbols}")

        print("\n--- Testing Price Fetcher for each symbol ---")
        
        for symbol in unique_symbols:
            print(f"Fetching {symbol}...")
            try:
                price = await price_fetcher.get_price_async(symbol)
                if price:
                    print(f"✅ {symbol}: {price}")
                else:
                    print(f"❌ {symbol}: Failed to fetch price")
            except Exception as e:
                print(f"❌ {symbol}: Error - {e}")

        print("\n--- Testing Bulk Update ---")
        result = await holdings_service.update_all_prices_async()
        print(f"Bulk Update Result: {result}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_updates())
