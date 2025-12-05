from app.database import engine
from sqlalchemy import text

def add_preferences_column():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN preferences JSON DEFAULT '{}'"))
            conn.commit()
            print("Successfully added preferences column to users table.")
        except Exception as e:
            print(f"Error (might already exist): {e}")

if __name__ == "__main__":
    add_preferences_column()
