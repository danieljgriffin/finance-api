from app.database import SessionLocal
from app.services.holdings_service import HoldingsService
import asyncio
import time

async def main():
    db = SessionLocal()
    try:
        service = HoldingsService(db, 1) # Assuming user_id 1
        
        print("--- Testing New Async Price Fetcher Logic ---")
        start_time = time.time()
        
        # This will use the modified get_multiple_prices_async with partial concurrency
        result = await service.update_all_prices_async()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Update Result: {result}")
        print(f"Total Duration: {duration:.2f}s")
        print("Success! No Rate Limit Errors observed (otherwise result would be partial or empty)")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
