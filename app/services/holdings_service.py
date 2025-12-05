from sqlalchemy.orm import Session
from app.models import Investment, PlatformCash, User
from app.schemas import InvestmentCreate
from datetime import datetime
from typing import List, Dict, Optional

class HoldingsService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_investments_by_platform(self) -> Dict[str, List[Dict]]:
        """Get all investments organized by platform"""
        investments = self.db.query(Investment).filter(Investment.user_id == self.user_id).all()
        data = {}
        
        # Initialize with empty lists for all platforms (could be dynamic or config based)
        default_platforms = [
            'Degiro', 'Trading212 ISA', 'EQ (GSK shares)', 
            'InvestEngine ISA', 'Crypto', 'HL Stocks & Shares LISA', 'Cash'
        ]
        
        for platform in default_platforms:
            data[platform] = []
        
        # Group investments by platform
        for investment in investments:
            if investment.platform not in data:
                data[investment.platform] = []
            data[investment.platform].append(investment.to_dict())
        
        return data

    def get_platform_cash(self, platform: str) -> float:
        """Get cash balance for a platform"""
        cash_entry = self.db.query(PlatformCash).filter(
            PlatformCash.user_id == self.user_id,
            PlatformCash.platform == platform
        ).first()
        return cash_entry.cash_balance if cash_entry else 0.0

    def update_platform_cash(self, platform: str, amount: float):
        """Update cash balance for a platform"""
        cash_entry = self.db.query(PlatformCash).filter(
            PlatformCash.user_id == self.user_id,
            PlatformCash.platform == platform
        ).first()
        
        if cash_entry:
            cash_entry.cash_balance = amount
            cash_entry.last_updated = datetime.utcnow()
        else:
            cash_entry = PlatformCash(
                user_id=self.user_id,
                platform=platform, 
                cash_balance=amount
            )
            self.db.add(cash_entry)
        
        self.db.commit()
        return cash_entry

    def add_investment(self, platform: str, investment_data: InvestmentCreate):
        """Add a new investment or aggregate with existing one"""
        # Check if this investment already exists in the platform
        existing_investment = self.db.query(Investment).filter(
            Investment.user_id == self.user_id,
            Investment.platform == platform,
            Investment.name == investment_data.name
        ).first()
        
        if existing_investment:
            # Calculate new aggregated values
            old_holdings = existing_investment.holdings
            old_amount_spent = existing_investment.amount_spent
            
            # Add new holdings and amount spent
            new_holdings = old_holdings + investment_data.holdings
            new_amount_spent = old_amount_spent + investment_data.amount_spent
            
            # Calculate new average buy price
            new_average_buy_price = new_amount_spent / new_holdings if new_holdings > 0 else 0
            
            # Update existing investment
            existing_investment.holdings = new_holdings
            existing_investment.amount_spent = new_amount_spent
            existing_investment.average_buy_price = new_average_buy_price
            existing_investment.last_updated = datetime.utcnow()
            
            # Update symbol if provided and not already set
            if investment_data.symbol and not existing_investment.symbol:
                existing_investment.symbol = investment_data.symbol
            
            self.db.commit()
            return existing_investment
        else:
            # Create new investment
            investment = Investment(
                user_id=self.user_id,
                platform=platform,
                name=investment_data.name,
                symbol=investment_data.symbol,
                holdings=investment_data.holdings,
                amount_spent=investment_data.amount_spent,
                average_buy_price=investment_data.average_buy_price,
                current_price=investment_data.current_price
            )
            
            self.db.add(investment)
            self.db.commit()
            self.db.refresh(investment)
            return investment

    def update_investment(self, investment_id: int, updates: Dict):
        """Update an existing investment"""
        investment = self.db.query(Investment).filter(
            Investment.id == investment_id,
            Investment.user_id == self.user_id
        ).first()
        
        if not investment:
            raise ValueError(f"Investment with ID {investment_id} not found")
        
        for key, value in updates.items():
            if hasattr(investment, key):
                setattr(investment, key, value)
        
        investment.last_updated = datetime.utcnow()
        self.db.commit()
        self.db.refresh(investment)
        return investment

    def delete_investment(self, investment_id: int):
        """Delete an investment"""
        investment = self.db.query(Investment).filter(
            Investment.id == investment_id,
            Investment.user_id == self.user_id
        ).first()
        
        if not investment:
            raise ValueError(f"Investment with ID {investment_id} not found")
        
        self.db.delete(investment)
        self.db.commit()

    def rename_platform(self, old_name: str, new_name: str):
        """Rename a platform across investments, cash entries, and preferences"""
        # Updates investments
        self.db.query(Investment).filter(
            Investment.user_id == self.user_id,
            Investment.platform == old_name
        ).update({Investment.platform: new_name}, synchronize_session=False)

        # Update cash entries
        self.db.query(PlatformCash).filter(
            PlatformCash.user_id == self.user_id,
            PlatformCash.platform == old_name
        ).update({PlatformCash.platform: new_name}, synchronize_session=False)

        # Update preferences if color exists
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if user:
            prefs = user.preferences
            if isinstance(prefs, str):
                try:
                    import json
                    prefs = json.loads(prefs)
                except:
                    prefs = {}
            elif not prefs:
                prefs = {}
            else:
                 # Ensure it's a dict copy if it's already a dict (SQLAlchemy MutableDict)
                 prefs = dict(prefs)

            colors = prefs.get('platform_colors', {})
            if old_name in colors:
                colors[new_name] = colors.pop(old_name)
                prefs['platform_colors'] = colors
                user.preferences = prefs

        self.db.commit()
        return {"status": "success", "old_name": old_name, "new_name": new_name}

    def update_platform_color(self, platform: str, color: str):
        """Update the custom color for a platform"""
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user:
            raise ValueError("User not found")
        
        prefs = user.preferences
        if isinstance(prefs, str):
            try:
                import json
                prefs = json.loads(prefs)
            except:
                prefs = {}
        elif not prefs:
            prefs = {}
        else:
            prefs = dict(prefs)
            
        colors = prefs.get('platform_colors', {})
        colors[platform] = color
        prefs['platform_colors'] = colors
        
        user.preferences = prefs
        self.db.commit()
        return {"status": "success", "platform": platform, "color": color}
    
    def get_platform_colors(self):
        """Get all custom platform colors"""
        user = self.db.query(User).filter(User.id == self.user_id).first()
        
        prefs = user.preferences if user else {}
        if isinstance(prefs, str):
            try:
                import json
                prefs = json.loads(prefs)
            except:
                prefs = {}
        
        if not prefs:
            return {}
            
        return prefs.get('platform_colors', {})
