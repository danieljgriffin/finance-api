import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

from app.database import engine, Base
from app.models import HistoricalNetWorth

def fix_db():
    print("Dropping HistoricalNetWorth table...")
    HistoricalNetWorth.__table__.drop(engine, checkfirst=True)
    
    print("Recreating tables...")
    Base.metadata.create_all(bind=engine)
    print("Success!")

if __name__ == "__main__":
    fix_db()
