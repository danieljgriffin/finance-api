"""
Backfill daily_net_worth_snapshots from existing NetWorthSnapshot data.

Run once after deployment to populate historical daily records:
    python backfill_daily_snapshots.py

This takes the last intraday snapshot of each day and inserts it
into the daily_net_worth_snapshots table.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from sqlalchemy import func, cast, Date
from app.database import SessionLocal
from app.models import NetWorthSnapshot, DailyNetWorthSnapshot

def backfill():
    db = SessionLocal()
    user_id = 1
    
    try:
        # Get the last snapshot for each day
        # Subquery: max timestamp per day
        subquery = db.query(
            cast(NetWorthSnapshot.timestamp, Date).label('snapshot_date'),
            func.max(NetWorthSnapshot.timestamp).label('max_ts')
        ).filter(
            NetWorthSnapshot.user_id == user_id
        ).group_by(
            cast(NetWorthSnapshot.timestamp, Date)
        ).subquery()
        
        # Join to get the full snapshot record for each day's latest entry
        daily_snapshots = db.query(NetWorthSnapshot).join(
            subquery,
            NetWorthSnapshot.timestamp == subquery.c.max_ts
        ).order_by(NetWorthSnapshot.timestamp.asc()).all()
        
        inserted = 0
        updated = 0
        
        for snapshot in daily_snapshots:
            snap_date = snapshot.timestamp.date()
            
            # Check if daily record already exists
            existing = db.query(DailyNetWorthSnapshot).filter(
                DailyNetWorthSnapshot.user_id == user_id,
                DailyNetWorthSnapshot.snapshot_date == snap_date
            ).first()
            
            if existing:
                existing.total_amount = snapshot.total_amount
                existing.assets_breakdown = snapshot.assets_breakdown
                updated += 1
            else:
                daily = DailyNetWorthSnapshot(
                    user_id=user_id,
                    snapshot_date=snap_date,
                    total_amount=snapshot.total_amount,
                    assets_breakdown=snapshot.assets_breakdown
                )
                db.add(daily)
                inserted += 1
        
        db.commit()
        print(f"Backfill complete: {inserted} inserted, {updated} updated, {inserted + updated} total daily records")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    backfill()
