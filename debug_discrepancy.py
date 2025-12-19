from app.database import SessionLocal
from app.models import Goal, Investment, PlatformCash
from sqlalchemy import func

def check_data():
    db = SessionLocal()
    
    # 1. Fetch Goals
    goals = db.query(Goal).all()
    print("\n--- GOALS ---")
    for g in goals:
        print(f"Goal: {g.title} | Amount: {g.target_amount} | Status: {g.status}")

    # 2. Calculate Live Net Worth
    total_holdings = db.query(func.sum(Investment.holdings * Investment.current_price)).scalar() or 0.0
    total_cash = db.query(func.sum(PlatformCash.cash_balance)).scalar() or 0.0
    net_worth = total_holdings + total_cash
    
    print(f"\n--- NET WORTH ---")
    print(f"Investments: {total_holdings}")
    print(f"Cash: {total_cash}")
    print(f"Total: {net_worth}")
    
    db.close()

if __name__ == "__main__":
    check_data()
