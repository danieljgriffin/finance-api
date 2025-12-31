from app.database import SessionLocal, engine
from sqlalchemy import text

def migrate():
    print("Migrating database...")
    with engine.connect() as connection:
        try:
            # Check if column exists first to avoid error
            check_query = text("SELECT column_name FROM information_schema.columns WHERE table_name='goals' AND column_name='completed_date';")
            result = connection.execute(check_query).fetchone()
            
            if not result:
                print("Adding completed_date column to goals table...")
                connection.execute(text("ALTER TABLE goals ADD COLUMN completed_date DATE;"))
                print("Column added successfully.")
            else:
                print("Column completed_date already exists.")
                
            connection.commit()
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
