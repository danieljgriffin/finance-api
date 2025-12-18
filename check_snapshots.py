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
    print("--- Current Time (UTC) ---")
    conn.execute(text("SET TIMEZONE='UTC'"))
    result = conn.execute(text("SELECT NOW()"))
    print(result.fetchone()[0])

    print("\n--- Net Worth Snapshots (Last 10) ---")
    # Correct table name is historical_net_worth
    result = conn.execute(text("SELECT * FROM historical_net_worth ORDER BY timestamp DESC LIMIT 10"))
    rows = list(result)
    if not rows:
        print("No rows found in historical_net_worth")
    else:
        for row in rows:
            print(row)
