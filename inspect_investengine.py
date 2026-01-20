import asyncio
import sys
import os
import yfinance as yf

# Add the parent directory to sys.path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import Investment
from app.utils.price_fetcher import PriceFetcher

async def inspect_invest_engine():
    db = SessionLocal()
    platform = 'InvestEngine ISA'
    
    print(f"Checking holdings for: {platform}")
    investments = db.query(Investment).filter(Investment.platform == platform).all()
    
    fetcher = PriceFetcher()
    
    total_current_db = 0
    total_prev_close = 0
    
    print(f"{'Symbol':<10} | {'Name':<30} | {'Holdings':<10} | {'DB Price':<10} | {'Fast Price':<10} | {'Prev Close':<10}")
    print("-" * 100)
    
    for inv in investments:
        symbol = inv.symbol
        if not symbol: continue
        
        # Get DB info
        db_price = inv.current_price
        
        # Get Yahoo Info
        ticker = yf.Ticker(symbol)
        try:
            fast_price = ticker.fast_info.last_price
            
            # Need regular info for previousClose
            info = ticker.info
            prev_close = info.get('previousClose')
            currency = info.get('currency')
            
            # Normalize if pence
            if currency == 'GBp' or (symbol.endswith('.L') and prev_close > 500):
                prev_close = prev_close / 100 if prev_close else 0
                if fast_price > 500: fast_price = fast_price / 100
                
            print(f"{symbol:<10} | {inv.name[:30]:<30} | {inv.holdings:<10.4f} | {db_price:<10.4f} | {fast_price:<10.4f} | {prev_close:<10.4f}")
            
            val_db = inv.holdings * db_price
            val_prev = inv.holdings * prev_close
            
            total_current_db += val_db
            total_prev_close += val_prev
            
        except Exception as e:
            print(f"{symbol}: Error {e}")
            
    # Add Cash
    from app.services.holdings_service import HoldingsService
    hs = HoldingsService(db, 1)
    cash = hs.get_platform_cash(platform)
    
    print("-" * 100)
    print(f"Cash Balance: £{cash:.2f}")
    print(f"Total Value (DB Current): £{total_current_db + cash:.2f}")
    print(f"Total Value (Prev Close): £{total_prev_close + cash:.2f}")
    
    target = 34619
    print(f"User Target: £{target}")
    
    diff_db = (total_current_db + cash) - target
    diff_prev = (total_prev_close + cash) - target
    
    print(f"Diff DB: {diff_db:.2f}")
    print(f"Diff Prev: {diff_prev:.2f}")

    db.close()

if __name__ == "__main__":
    asyncio.run(inspect_invest_engine())
