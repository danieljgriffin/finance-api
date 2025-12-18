from sqlalchemy import create_engine, text
from app.models import HistoricalNetWorth, User
from app.database import SessionLocal
from datetime import datetime, timedelta
import random
import os
from dotenv import load_dotenv
import math

load_dotenv()

db = SessionLocal()

def seed_intraday_data():
    print("Seeding intraday data...")
    user = db.query(User).first()
    if not user:
        print("No user found")
        return

    # Get current total from networth service logic (approximation)
    # Or just use a base value since we are mocking
    base_net_worth = 121000.0 
    
    # Generate data for last 24 hours, every 15 mins
    start_time = datetime.utcnow() - timedelta(hours=24)
    entries = []
    
    current_time = start_time
    while current_time <= datetime.utcnow():
        # Add some random walk
        import random
        # Create a realistic looking curve: sine wave + random noise
        # 24h sine wave
        time_seed = current_time.hour + (current_time.minute / 60.0)
        daily_pattern = math.sin((time_seed / 24.0) * 2 * math.pi) * 500
        noise = random.uniform(-200, 200)
        
        value = base_net_worth + daily_pattern + noise
        
        entry = HistoricalNetWorth(
            user_id=user.id,
            timestamp=current_time,
            net_worth=value,
            platform_breakdown={"MockPlatform": value} # Simplified breakdown
        )
        db.add(entry)
        current_time += timedelta(minutes=15)
        
    db.commit()
    print(f"Added {len(entries)} mock entries.")

if __name__ == "__main__":
    seed_intraday_data()
