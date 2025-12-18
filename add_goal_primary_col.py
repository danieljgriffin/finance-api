from sqlalchemy import create_engine, text
from app.database import SQLALCHEMY_DATABASE_URI
import os

def add_is_primary_column():
    print("Connecting to database...")
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    
    with engine.connect() as conn:
        print("Checking if column exists...")
        # Check column existence (Postgres specific)
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='goals' AND column_name='is_primary'"))
        if result.fetchone():
            print("Column 'is_primary' already exists.")
            return

        print("Adding column 'is_primary'...")
        conn.execute(text("ALTER TABLE goals ADD COLUMN is_primary BOOLEAN DEFAULT FALSE"))
        conn.commit()
        print("Column added successfully.")

if __name__ == "__main__":
    add_is_primary_column()
