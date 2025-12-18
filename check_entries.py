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
    print("--- NetWorth Entries (Last 20) ---")
    result = conn.execute(text("SELECT year, month, total_networth, created_at FROM networth_entries ORDER BY year DESC, id DESC LIMIT 20"))
    for row in result:
        print(row)
