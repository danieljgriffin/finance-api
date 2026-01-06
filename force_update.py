from app.database import SessionLocal
from app.models import Investment
from app.services.holdings_service import HoldingsService

db = SessionLocal()
service = HoldingsService(db, 1) # Assuming user_id 1

print("--- Checking Symbols for Whitespace ---")
investments = db.query(Investment).all()
for inv in investments:
    if inv.symbol:
        print(f"'{inv.symbol}' (Len: {len(inv.symbol)}) - Platform: {inv.platform}")

print("\n--- Manually Triggering Update ---")
result = service.update_all_prices()
print(f"Update Result: {result}")

print("\n--- Checking Updated Prices ---")
# Re-query
investments = db.query(Investment).all()
for inv in investments:
    if inv.symbol and inv.platform in ('Trading212 ISA', 'InvestEngine ISA'):
        print(f"{inv.platform} - {inv.symbol}: {inv.current_price} (Updated: {inv.last_updated})")
