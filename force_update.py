import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the parent directory to sys.path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.services.holdings_service import HoldingsService

# Configure logging to see our new logs
logging.basicConfig(level=logging.INFO)

async def force_update():
    print(f"Starting force update at {datetime.now()}")
    db = SessionLocal()
    try:
        service = HoldingsService(db, user_id=1)
        
        # 1. Update Prices
        print("Trigerring update_all_prices_async...")
        result = await service.update_all_prices_async()
        print(f"Update Result: {result}")
        
        # 2. Check a few prices
        from app.models import Investment
        invs = db.query(Investment).filter(Investment.platform == 'Degiro').limit(3).all()
        for inv in invs:
             print(f"  {inv.symbol}: {inv.current_price} (Updated: {inv.last_updated})")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(force_update())
