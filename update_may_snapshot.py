from app.database import SessionLocal
from app.models import MonthlyFinancialRecord
from datetime import date

def update_may_snapshot():
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
        old_net_worth = may_record.net_worth
        target_net_worth = 123409.0
        
        print(f"User {user_id}: Updating May net worth from {old_net_worth} to {target_net_worth}")
        may_record.net_worth = target_net_worth
        
        # Scale the platform breakdown
        if may_record.details and old_net_worth > 0:
            scale_factor = target_net_worth / old_net_worth
            new_details = {}
            for platform, amount in may_record.details.items():
                new_details[platform] = round(amount * scale_factor, 2)
            may_record.details = new_details
    
    db.commit()
    print("Done!")
    
if __name__ == "__main__":
    update_may_snapshot()
