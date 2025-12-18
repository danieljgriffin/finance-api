from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("--- Daily Historical Net Worth (One Row) ---")
    # Using result.keys() from the cursor if possible, or just print the row mapping
    result = conn.execute(text("SELECT * FROM daily_historical_net_worth LIMIT 1"))
    
    # Print column names
    print("Columns:", result.keys())
    
    row = result.fetchone()
    if row:
        print("Data:", row)
    else:
        print("Table is empty")
