from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("--- Networth Entries Ownership ---")
    
    # Check columns
    cols = conn.execute(text("SELECT * FROM networth_entries LIMIT 0")).keys()
    print("Columns:", list(cols))

    print("\nCounts by Year and UserID:")
    result = conn.execute(text("SELECT year, user_id, COUNT(*) FROM networth_entries GROUP BY year, user_id ORDER BY year, user_id"))
    for row in result:
        print(row)
        
    print("\nCheck if there are entries with NULL user_id:")
    result = conn.execute(text("SELECT count(*) FROM networth_entries WHERE user_id IS NULL"))
    print("Null user_id count:", result.scalar())
