from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("--- Daily Historical Net Worth (Last 10) ---")
    result = conn.execute(text("SELECT * FROM daily_historical_net_worth ORDER BY date DESC LIMIT 10"))
    rows = list(result)
    if not rows:
        print("No rows found in daily_historical_net_worth")
    else:
        for row in rows:
            print(row)
