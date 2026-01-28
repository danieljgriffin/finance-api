"""Fix META price directly in database"""
import sys
sys.path.insert(0, '/Users/danielgriffin/Documents/Apps/WealthTrackerStack/finance-api')

from app.database import SessionLocal
from app.models import Investment
from app.utils.price_fetcher import PriceFetcher

db = SessionLocal()
pf = PriceFetcher()

# Find META
meta = db.query(Investment).filter(Investment.symbol == 'META', Investment.user_id == 1).first()

if meta:
    print(f"Found META: {meta.name}")
    print(f"Current price in DB: £{meta.current_price}")
    
    # Fetch fresh price
    price = pf.get_price('META')
    if price:
        print(f"Fetched new price: £{price:.2f}")
        meta.current_price = price
        db.commit()
        print("✅ Updated META price in database!")
    else:
        print("❌ Failed to fetch price from Yahoo/Google")
        # Fallback: use approximate value
        # META is ~$700 USD, so ~£560 GBP
        rate = pf.get_usd_to_gbp_rate()
        approx_price = 700 * rate
        print(f"Using approximate: £{approx_price:.2f} (700 USD * {rate} rate)")
        meta.current_price = approx_price
        db.commit()
        print("✅ Updated META with approximate price!")
else:
    print("META not found in database")

db.close()
