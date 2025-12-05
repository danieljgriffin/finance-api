from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("DATABASE_URL not found")
    exit(1)

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

print("Tables in database:")
for table_name in inspector.get_table_names():
    print(f"- {table_name}")
    
    # Optional: print columns for tables that look relevant
    if "income" in table_name or "invest" in table_name:
        print(f"  Columns in {table_name}:")
        for column in inspector.get_columns(table_name):
            print(f"    - {column['name']} ({column['type']})")
