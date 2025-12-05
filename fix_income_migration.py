from sqlalchemy import create_engine, text, inspect
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found")
    exit(1)

engine = create_engine(DATABASE_URL)

def run_migration():
    with engine.connect() as conn:
        print("Checking users table...")
        result = conn.execute(text("SELECT id FROM users WHERE id = 1"))
        if not result.first():
            print("User ID 1 not found. Creating default user...")
            conn.execute(text("INSERT INTO users (id, email, created_at) VALUES (1, 'default@example.com', NOW())"))
            conn.commit()
            print("Default user created.")
        else:
            print("User ID 1 exists.")

        print("Checking income_data table columns...")
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('income_data')]
        
        if 'user_id' not in columns:
            print("Adding user_id column to income_data...")
            # Add column nullable first
            conn.execute(text("ALTER TABLE income_data ADD COLUMN user_id INTEGER"))
            
            # Update existing rows to user_id = 1
            print("Updating existing rows...")
            conn.execute(text("UPDATE income_data SET user_id = 1 WHERE user_id IS NULL"))
            
            # Add FK constraint
            print("Adding FK constraint...")
            conn.execute(text("ALTER TABLE income_data ADD CONSTRAINT fk_income_users FOREIGN KEY (user_id) REFERENCES users(id)"))
            
            # Make not nullable
            print("Setting user_id to NOT NULL...")
            conn.execute(text("ALTER TABLE income_data ALTER COLUMN user_id SET NOT NULL"))
            
            conn.commit()
            print("Migration successful: user_id added to income_data.")
        else:
            print("user_id already exists in income_data.")

if __name__ == "__main__":
    run_migration()
