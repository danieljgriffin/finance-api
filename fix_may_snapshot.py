from app.database import SessionLocal
from app.models import MonthlyFinancialRecord
from datetime import date

def fix_may_snapshot():
    db = SessionLocal()
    
    # Find all May 2026 records
    may_records = db.query(MonthlyFinancialRecord).filter(
        MonthlyFinancialRecord.period_date == date(2026, 5, 1)
    ).all()
    
    if not may_records:
        print("No May 2026 records found.")
        return
        
    for may_record in may_records:
        user_id = may_record.user_id
        
        # Get April 2026 record for this user
        april_record = db.query(MonthlyFinancialRecord).filter(
            MonthlyFinancialRecord.user_id == user_id,
            MonthlyFinancialRecord.period_date == date(2026, 4, 1)
        ).first()
        
        if not april_record:
            print(f"April 2026 record not found for user {user_id}. Skipping.")
            continue
            
        print(f"User {user_id}: Updating May baseline from {may_record.net_worth} to {april_record.net_worth}")
        
        may_record.net_worth = april_record.net_worth
        may_record.details = april_record.details
    
    db.commit()
    print("Done!")
    
if __name__ == "__main__":
    fix_may_snapshot()
