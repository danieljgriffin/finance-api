import sys
import os
from datetime import datetime, date
import calendar
import json

# Add current dir to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON, Date
from sqlalchemy.orm import sessionmaker, declarative_base
from app.database import Base, SQLALCHEMY_DATABASE_URI as DATABASE_URL
from app.models import NetWorthSnapshot, MonthlyFinancialRecord

# Define Old Models for reading
OldBase = declarative_base()

class OldNetworthEntry(OldBase):
    __tablename__ = 'networth_entries'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    year = Column(Integer)
    month = Column(String)
    platform_data = Column(Text)
    total_networth = Column(Float)
    created_at = Column(DateTime)

class OldHistoricalNetWorth(OldBase):
    __tablename__ = 'historical_net_worth'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    timestamp = Column(DateTime)
    net_worth = Column(Float)
    platform_breakdown = Column(JSON)
    created_at = Column(DateTime)

class OldDailyHistoricalNetWorth(OldBase):
    __tablename__ = 'daily_historical_net_worth'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    net_worth = Column(Float)
    platform_breakdown = Column(JSON)
    created_at = Column(DateTime)

def parse_month(month_str):
    month_str = month_str.replace("1st ", "").strip()
    month_map = {m: i for i, m in enumerate(calendar.month_abbr) if i}
    full_month_map = {m: i for i, m in enumerate(calendar.month_name) if i}
    
    if month_str in month_map:
        return month_map[month_str]
    if month_str in full_month_map:
        return full_month_map[month_str]
    
    legacy_map = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
        '31st Dec': 12
    }
    if "31st Dec" in month_str:
        return 12
        
    return datetime.now().month

def run_migration():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Creating new tables...")
    Base.metadata.create_all(engine)

    # 1. Migrate NetworthEntry -> MonthlyFinancialRecord
    print("Migrating NetworthEntry...")
    old_entries = session.query(OldNetworthEntry).all()
    count = 0
    for old in old_entries:
        try:
            m = parse_month(old.month)
            # 1st of month by default
            p_date = date(old.year, m, 1)
            
            # Check if exists (idempotency)
            exists = session.query(MonthlyFinancialRecord).filter_by(
                user_id=old.user_id,
                period_date=p_date
            ).first()
            
            if not exists:
                details = {}
                if old.platform_data:
                    try:
                        details = json.loads(old.platform_data)
                    except:
                        pass
                
                new_record = MonthlyFinancialRecord(
                    user_id=old.user_id,
                    period_date=p_date,
                    net_worth=old.total_networth,
                    details=details,
                    created_at=old.created_at or datetime.utcnow()
                )
                session.add(new_record)
                count += 1
        except Exception as e:
            print(f"Skipping entry {old.id}: {e}")

    print(f"Migrated {count} monthly records.")

    # 2. Migrate HistoricalNetWorth -> NetWorthSnapshot
    print("Migrating HistoricalNetWorth (High Frequency)...")
    old_hist = session.query(OldHistoricalNetWorth).all()
    h_count = 0
    for old in old_hist:
        exists = session.query(NetWorthSnapshot).filter_by(
            timestamp=old.timestamp,
            user_id=old.user_id # Old table had user_id
        ).first()

        if not exists:
            # handle case where breakdown is string or dict
            bd = old.platform_breakdown
            if isinstance(bd, str):
                try: bd = json.loads(bd)
                except: bd = {}
            
            snap = NetWorthSnapshot(
                user_id=old.user_id,
                timestamp=old.timestamp,
                total_amount=old.net_worth,
                assets_breakdown=bd or {},
                currency='GBP',
                created_at=old.created_at or datetime.utcnow()
            )
            session.add(snap)
            h_count += 1
    
    print(f"Migrated {h_count} historical snapshots.")

    # 3. Migrate DailyHistoricalNetWorth -> NetWorthSnapshot
    # This table had NO user_id. We assume user_id=1 (or first user).
    # Since this is a local app refactor, we can assume user_id=1 if not present.
    # We will only insert if we don't have a snapshot at that exact time already.
    print("Migrating DailyHistoricalNetWorth...")
    
    # Try to find a default user id
    default_user_id = 1
    
    old_daily = session.query(OldDailyHistoricalNetWorth).all()
    d_count = 0
    for old in old_daily:
        exists = session.query(NetWorthSnapshot).filter_by(
            timestamp=old.timestamp
        ).first()
        
        if not exists:
             # handle case where breakdown is string or dict
            bd = old.platform_breakdown
            if isinstance(bd, str):
                try: bd = json.loads(bd)
                except: bd = {}

            snap = NetWorthSnapshot(
                user_id=default_user_id,
                timestamp=old.timestamp,
                total_amount=old.net_worth,
                assets_breakdown=bd or {},
                currency='GBP',
                created_at=old.created_at or datetime.utcnow()
            )
            session.add(snap)
            d_count += 1

    print(f"Migrated {d_count} daily snapshots.")
    
    session.commit()
    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
