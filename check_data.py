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
    print("--- Users ---")
    result = conn.execute(text("SELECT id, email FROM users"))
    for row in result:
        print(row)

    print("\n--- Income Data (First 10 rows) ---")
    result = conn.execute(text("SELECT * FROM income_data LIMIT 10"))
    rows = list(result)
    if not rows:
        print("No rows found in income_data")
    else:
        for row in rows:
            print(row)
            
    print("\n--- Monthly Investments (First 5 rows) ---")
    result = conn.execute(text("SELECT * FROM monthly_investments LIMIT 5"))
    for row in result:
        print(row)
