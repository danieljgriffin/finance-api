from app.database import SessionLocal
from app.models import Investment, User

db = SessionLocal()

try:
    # Get the user (assuming user_id=1 for single user app)
    user = db.query(User).first()
    if not user:
        print("No user found")
    else:
        print(f"User: {user.email} (ID: {user.id})")
        
        investments = db.query(Investment).filter(Investment.user_id == user.id).all()
        print(f"Found {len(investments)} investments")
        
        print(f"{'Platform':<20} | {'Name':<30} | {'Symbol':<10} | {'Holdings':<10} | {'Cur Price':<10} | {'Last Upd':<20}")
        print("-" * 110)
        
        for inv in investments:
            symbol = inv.symbol if inv.symbol else "MISSING"
            print(f"{inv.platform:<20} | {inv.name[:28]:<30} | {symbol:<10} | {inv.holdings:<10.4f} | {inv.current_price:<10.2f} | {inv.last_updated}")

finally:
    db.close()
