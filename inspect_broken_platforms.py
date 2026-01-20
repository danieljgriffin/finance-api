import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import Investment
from datetime import datetime

def inspect_broken_platforms():
    db = SessionLocal()
    broken_platforms = ['InvestEngine ISA', 'Degiro', 'EQ (GSK shares)', 'Trading212 ISA']
    
    print(f"Checking platforms: {broken_platforms}")
    print("-" * 80)
    
    for platform in broken_platforms:
        print(f"\nPlatform: {platform}")
        investments = db.query(Investment).filter(Investment.platform == platform).all()
        
        if not investments:
            print("  No investments found.")
            continue
            
        for inv in investments:
            print(f"  ID: {inv.id} | Name: {inv.name} | Symbol: {inv.symbol} | updated: {inv.last_updated} | Price: {inv.current_price}")
            
    db.close()

if __name__ == "__main__":
    inspect_broken_platforms()
