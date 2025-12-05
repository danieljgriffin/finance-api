from app.database import engine
from sqlalchemy import text

def fix_schema():
    print("Creating all tables...")
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    
    with engine.connect() as conn:
        print("Checking and fixing schema...")
        
        # List of tables that need user_id
        tables = [
            'investments', 
            'goals', 
            'networth_entries', 
            'platform_cash', 
            'expenses'
        ]
        
        for table in tables:
            try:
                # Check if column exists
                check_sql = text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='{table}' AND column_name='user_id';
                """)
                result = conn.execute(check_sql).fetchone()
                
                if not result:
                    print(f"Adding user_id to {table}...")
                    # Add column with default value 1
                    add_sql = text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 1;")
                    conn.execute(add_sql)
                    conn.commit()
                    print(f"Successfully added user_id to {table}")
                else:
                    print(f"Table {table} already has user_id")
                    
            except Exception as e:
                print(f"Skipping {table} (might not exist or other error): {str(e)}")
                conn.rollback()

if __name__ == "__main__":
    fix_schema()
