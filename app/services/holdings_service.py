from sqlalchemy.orm import Session
from app.models import Investment, PlatformCash, User
from app.schemas import InvestmentCreate
from datetime import datetime
from typing import List, Dict, Optional, Any
import asyncio

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
    
    
    # Default colors matching Web App Tailwind classes
    DEFAULT_PLATFORM_COLORS = {
        'Degiro': '#2563EB',         # bg-blue-600
        'Trading212 ISA': '#10B981', # bg-emerald-500
        'EQ (GSK shares)': '#F43F5E',# bg-rose-500
        'InvestEngine ISA': '#F97316',# bg-orange-500
        'Crypto': '#A855F7',         # bg-purple-500
        'HL Stocks & Shares LISA': '#0EA5E9', # bg-sky-500
        'Cash': '#14B8A6',           # bg-teal-500
        'Vanguard': '#DC2626',       # bg-red-600
        'Other': '#64748B'           # bg-slate-500
    }

    def get_platform_colors(self):
        """Get all custom platform colors (Defaults + User Overrides)"""
        user = self.db.query(User).filter(User.id == self.user_id).first()
        
        prefs = user.preferences if user else {}
        if isinstance(prefs, str):
            try:
                import json
                prefs = json.loads(prefs)
            except:
                prefs = {}
        
        user_colors = prefs.get('platform_colors', {}) if prefs else {}
        
        # Merge: Defaults < User Overrides
        # We start with defaults, then update with user specific
        final_colors = self.DEFAULT_PLATFORM_COLORS.copy()
        if user_colors:
            final_colors.update(user_colors)
            
        return final_colors

    def update_all_prices(self) -> Dict[str, Any]:
        """Update live prices for all investments"""
        from app.utils.price_fetcher import PriceFetcher
        price_fetcher = PriceFetcher()
        
        investments = self.db.query(Investment).filter(Investment.user_id == self.user_id).all()
        
        updated_count = 0
        symbols = [inv.symbol for inv in investments if inv.symbol]
        
        # Eliminate duplicates
        symbols = list(set(symbols))
        
        if not symbols:
            return {"status": "skipped", "message": "No symbols to update"}
            
        prices = price_fetcher.get_multiple_prices(symbols)
        
        for investment in investments:
            if investment.symbol and investment.symbol in prices:
                investment.current_price = prices[investment.symbol]
                investment.last_updated = datetime.now()
                updated_count += 1
                
        self.db.commit()
        return {"status": "success", "updated_count": updated_count}

    async def update_all_prices_async(self) -> Dict[str, Any]:
        """Update live prices for all investments asynchronously"""
        from app.utils.price_fetcher import PriceFetcher
        price_fetcher = PriceFetcher()
        
        investments = self.db.query(Investment).filter(Investment.user_id == self.user_id).all()
        
        updated_count = 0
        symbols = [inv.symbol for inv in investments if inv.symbol]
        
        # Eliminate duplicates
        symbols = list(set(symbols))
        
        if not symbols:
            return {"status": "skipped", "message": "No symbols to update"}
            
        prices = await price_fetcher.get_multiple_prices_async(symbols)
        
        for investment in investments:
            if investment.symbol and investment.symbol in prices:
                investment.current_price = prices[investment.symbol]
                investment.last_updated = datetime.now()
                updated_count += 1
                
        self.db.commit()
        return {"status": "success", "updated_count": updated_count}
                
    
    def normalize_trading212_ticker(self, ticker: str) -> str:
        """Convert Trading 212 ticker format to standard format"""
        if ticker.endswith('_US_EQ'):
            return ticker.replace('_US_EQ', '')
        elif ticker.endswith('_EQ'):
            base = ticker.replace('_EQ', '')
            # T212 sometimes uses 'l' at the end for UK stocks (e.g. RRl -> RR.L)
            if base.endswith('l'):
                return f"{base[:-1]}.L"
            return base
        return ticker

    def remap_ticker(self, symbol: str) -> str:
        """Remap old ticker symbols to current ones"""
        TICKER_REMAPPING = {
            'FB': 'META',
            'RRI': 'RR.L' # Specific fix for user's Rolls Royce
        }
        return TICKER_REMAPPING.get(symbol, symbol)

    def get_company_name_safe(self, symbol: str, default: str) -> str:
        """Dynamically fetch company name from Yahoo Finance with fallback"""
        import yfinance as yf
        try:
            # We don't want to block the sync too long, so we try quickly or fall back
            ticker = yf.Ticker(symbol)
            # Accessing .info triggers the fetch
            info = ticker.info 
            return info.get('longName') or info.get('shortName') or default
        except Exception:
            return default

    async def sync_trading212_investments(self, api_key_id: str, api_secret_key: str) -> Dict[str, Any]:
        """Import/Sync investments from Trading212 (Full Replace)"""
        from app.services.trading212_service import Trading212Service
        from app.utils.price_fetcher import PriceFetcher
        import json
        
        # DEBUG: Clear log
        with open("debug_log.txt", "w") as f:
            f.write(f"Starting T212 Sync at {datetime.now()}\n")
        
        t212 = Trading212Service(api_key_id, api_secret_key)
        
        loop = asyncio.get_running_loop()
        portfolio = await loop.run_in_executor(None, t212.fetch_portfolio)

        price_fetcher = PriceFetcher()
        
        # 1. Clear existing Trading212 investments
        target_platform = 'Trading212 ISA'
        deleted_count = self.db.query(Investment).filter(
            Investment.user_id == self.user_id,
            Investment.platform == target_platform
        ).delete()
        
        added_count = 0
        
        # Prefetch rates if possible, or fetch on demand
        usd_to_gbp = price_fetcher.get_usd_to_gbp_rate()
        
        with open("debug_log.txt", "a") as f:
             f.write(f"USD to GBP Rate: {usd_to_gbp}\n")
        
        for item in portfolio:
            raw_ticker = item.get('ticker', '')
            quantity = float(item.get('quantity', 0))
            avg_price = float(item.get('averagePrice', 0))
            currency = item.get('currency', '').upper()
            
            with open("debug_log.txt", "a") as f:
                f.write(f"Item: {raw_ticker} | Cur: '{currency}' | AvgPrice: {avg_price} | Raw: {json.dumps(item)}\n")
            
            # Step 1: Normalize (NVDA_US_EQ -> NVDA)
            normalized_symbol = self.normalize_trading212_ticker(raw_ticker)
            
            # Step 2: Remap (FB -> META)
            final_symbol = self.remap_ticker(normalized_symbol)
            
            # Step 3: Get Name (Dynamic Lookup)
            fallback_name = item.get('name') or final_symbol
            company_name = self.get_company_name_safe(final_symbol, fallback_name)

            # Fallback: Infer currency from ticker suffix if missing
            if not currency:
                if raw_ticker.endswith('_US_EQ'):
                    currency = 'USD'
                elif raw_ticker.endswith('_EQ') or final_symbol.endswith('.L'):
                    # Likely UK -> Default to 'GBX' (Pence) check logic later or set as 'GBX' if price high
                    # But let's set a temporary flag or just handle in the main logic below if I restructure it.
                    # Simplest: Just set currency='GBX' if it looks like UK and price is high, or 'GBP' otherwise.
                    # Actually, let's just use the existing blocks.
                    pass

            with open("debug_log.txt", "a") as f:
                f.write(f"  -> Inferred Currency: '{currency}'\n")

            # Step 4: Currency Conversion
            # Option 1: Profit-First Reverse Engineer for USD (captures historic FX)
            
            if currency == 'USD':
                # Formula: Cost_GBP = (CurrentVal_USD * Rate) - PPL_GBP
                # Avg_GBP = Cost_GBP / Quantity
                
                # Use current price from T212 to match their PPL calculation context
                t212_current_price = float(item.get('currentPrice', 0))
                # PPL is total profit in account currency (GBP)
                t212_ppl = float(item.get('ppl', 0))
                
                if quantity > 0 and t212_current_price > 0:
                    current_val_gbp = (quantity * t212_current_price) * usd_to_gbp
                    total_cost_gbp = current_val_gbp - t212_ppl
                    calculated_avg = total_cost_gbp / quantity
                    
                    with open("debug_log.txt", "a") as f:
                        f.write(f"  -> Profit-Based Calc: (Val {current_val_gbp:.2f} - PPL {t212_ppl}) / Qty {quantity} = {calculated_avg:.2f}\n")
                    
                    avg_price = calculated_avg
                else:
                    # Fallback if missing data
                    avg_price = avg_price * usd_to_gbp
            
            elif currency in ['GBX', 'GBP'] or (not currency and (raw_ticker.endswith('_EQ') or final_symbol.endswith('.L'))):
                # Handle Pence vs Pounds
                # T212 often returns UK stocks in Pence (GBX) but labels as GBP sometimes?
                # Heuristic: if currency is GBX OR (currency is GBP and price is suspiciously high > 500p)
                
                if currency == 'GBX':
                    avg_price = avg_price / 100.0
                    with open("debug_log.txt", "a") as f:
                        f.write(f"  -> Converted GBX to GBP {avg_price}\n")
                elif currency == 'GBP':
                    # Sometimes T212 might say GBP but send pence? 
                    # Let's rely on magnitude heuristic for UK stocks if no clear GBX 
                    # (Rolls Royce ~650 -> 6.50)
                    if avg_price > 500:
                         avg_price = avg_price / 100.0
                         with open("debug_log.txt", "a") as f:
                            f.write(f"  -> Converted GBP(Pence) to GBP {avg_price}\n")
                else: 
                     # No explicit currency but looks like UK (suffix or .L)
                     # Fallback heuristic
                     if avg_price > 500:
                          avg_price = avg_price / 100.0
                          with open("debug_log.txt", "a") as f:
                                f.write(f"  -> Fallback Converted UK Pence to GBP {avg_price}\n")
            
            elif currency == 'EUR':
                # Optional: Add EUR support if needed
                # For now, treat as 1:0.83 (approx) or fetch rate?
                # Let's just log warning and leave as is for now to avoid breaking
                pass
            
            # Fallback for weird cases: if no currency, rely on symbol
            elif not currency:
                 if final_symbol.endswith('.L') and avg_price > 500:
                      avg_price = avg_price / 100.0
                      with open("debug_log.txt", "a") as f:
                            f.write(f"  -> Fallback Converted Pence to GBP {avg_price}\n")

            target_amount_spent = quantity * avg_price
            
            new_inv = Investment(
                user_id=self.user_id,
                platform=target_platform,
                name=company_name, 
                symbol=final_symbol,
                holdings=quantity,
                average_buy_price=avg_price,
                amount_spent=target_amount_spent,
                current_price=0 
            )
            self.db.add(new_inv)
            added_count += 1
                
        self.db.commit()
        

        # Trigger price update
        await self.update_all_prices_async()
        
        return {
            "status": "success",
            "message": f"Synced {len(portfolio)} investments from Trading212",
            "added": added_count,
            "deleted": deleted_count
        }

    def save_trading212_credentials(self, api_key_id: str, api_secret_key: str) -> bool:
        """Encrypt and save T212 credentials to user preferences"""
        from app.utils.security import encrypt_value
        from app.models import User
        from sqlalchemy.orm.attributes import flag_modified
        
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user: return False
        
        # Ensure we work with a copy or new dict
        prefs = dict(user.preferences) if user.preferences else {}
        
        t212_config = {
            "enabled": True,
            "api_key_id_enc": encrypt_value(api_key_id),
            "api_secret_key_enc": encrypt_value(api_secret_key),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        prefs['trading212_sync'] = t212_config
        user.preferences = prefs
        flag_modified(user, "preferences")
        
        self.db.commit()
        return True

    def get_trading212_credentials(self) -> Optional[Dict[str, str]]:
        """Retrieve and decrypt T212 credentials"""
        from app.utils.security import decrypt_value
        from app.models import User
        
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user or not user.preferences: return None
        
        prefs = user.preferences
        t212_config = prefs.get('trading212_sync')
        
        if not t212_config or not t212_config.get('enabled'):
            return None
            
        try:
            return {
                "api_key_id": decrypt_value(t212_config.get('api_key_id_enc')),
                "api_secret_key": decrypt_value(t212_config.get('api_secret_key_enc'))
            }
        except Exception:
            return None
        
        return {
            "status": "success", 
            "added": added_count,
            "deleted": deleted_count,
            "total_synced": len(portfolio)
        }
