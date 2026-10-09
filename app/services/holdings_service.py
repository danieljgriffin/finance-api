from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.models import Investment, PlatformCash, User
from app.schemas import InvestmentCreate
from app.utils.portfolio import is_standalone_cash_platform
from datetime import datetime
from typing import List, Dict, Optional, Any
import asyncio

class HoldingsService:
    TRADING212_PLATFORMS = {
        'isa': 'Trading212 ISA',
        'gia': 'Trading212 GIA',
    }

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
        
        # Add platforms that exist in PlatformCash (e.g. "Other") but have no investments yet
        cash_platforms = self.db.query(PlatformCash.platform).filter(
            PlatformCash.user_id == self.user_id
        ).distinct().all()
        
        # cash_platforms is list of tuples [('Other',), ('Degiro',)]
        dynamic_platforms = [p[0] for p in cash_platforms]
        
        # Merge all known platforms
        all_platforms = set(default_platforms) | set(dynamic_platforms)
        
        for platform in all_platforms:
            data[platform] = []
        
        # Group investments by platform
        for investment in investments:
            if investment.platform not in data:
                data[investment.platform] = []
            data[investment.platform].append(investment.to_dict())
        
        return data

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get full portfolio summary with calculated totals"""
        # 1. Fetch Data
        investments_map = self.get_investments_by_platform()
        colors = self.get_platform_colors()
        
        # 2. Results Containers
        platform_summaries = []
        
        global_value = 0.0
        global_invested = 0.0 # Cost of investments only
        global_pl = 0.0
        
        # 3. Process Each Platform
        for platform_name, investments_data in investments_map.items():
            # Convert dicts back to objects or use as is? 
            # get_investments_by_platform returns list of dicts from .to_dict()
            # But schemas expects models or dicts. Let's use the dicts.
            
            # Fetch Cash
            cash = self.get_platform_cash(platform_name)
            
            # Investments Calcs
            plat_invested = 0.0
            plat_current_inv_val = 0.0
            
            for inv in investments_data:
                # Calculate P/L for investment if not present
                # Dict from SQLAlchemy defaults usually just has columns
                cost = inv.get('amount_spent', 0)
                # Fallback cost
                if cost == 0 and inv.get('holdings', 0) > 0:
                     cost = inv.get('holdings') * inv.get('average_buy_price')
                
                val = inv.get('holdings', 0) * inv.get('current_price', 0)
                
                plat_invested += cost
                plat_current_inv_val += val
                
            # Platform Totals
            plat_total_value = plat_current_inv_val + cash
            
            # Trading 212 cash is part of account value, but is not investment profit.
            # Preserve the legacy calculation for other manually managed platforms.
            if platform_name in self.TRADING212_PLATFORMS.values():
                plat_pl = plat_current_inv_val - plat_invested
            else:
                plat_pl = plat_total_value - plat_invested
            
            plat_pl_percent = (plat_pl / plat_invested * 100) if plat_invested != 0 else 0
            
            # Sort investments by Value Descending (User Request)
            investments_data.sort(key=lambda x: (x.get('holdings', 0) * x.get('current_price', 0)), reverse=True)
            
            summary = {
                "name": platform_name,
                "total_value": plat_total_value,
                "total_invested": plat_invested,
                "total_pl": plat_pl,
                "total_pl_percent": plat_pl_percent,
                "cash_balance": cash,
                "investments": investments_data,
                "color": colors.get(platform_name, "#808080")
            }
            
            platform_summaries.append(summary)
            
            # Global Accumulation
            global_value += plat_total_value
            global_invested += plat_invested
            # global_pl is derived from totals now, or we can sum plat_pl (mathematically same)
            global_pl += plat_pl
            
        # 4. Global Percent. Sum the platform P/L values so Trading 212 cash is
        # not reintroduced as profit after being excluded above.
        global_pl_percent = (global_pl / global_invested * 100) if global_invested != 0 else 0
        
        # 5. Sort by value descending, except standalone Cash is always last.
        platform_summaries.sort(key=lambda item: (
            is_standalone_cash_platform(item['name']),
            -item['total_value'],
            item['name'].casefold(),
        ))
        
        return {
            "total_value": global_value,
            "total_invested": global_invested,
            "total_pl": global_pl,
            "total_pl_percent": global_pl_percent,
            "platforms": platform_summaries
        }

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
        flag_modified(user, "preferences")
        self.db.commit()
        return {"status": "success", "platform": platform, "color": color}
    
    def delete_platform(self, platform_name: str):
        """Delete a platform, its cash balance, and all associated investments"""
        # 1. Delete PlatformCash entry
        self.db.query(PlatformCash).filter(
            PlatformCash.user_id == self.user_id,
            PlatformCash.platform == platform_name
        ).delete()
        
        # 2. Delete all Investments for this platform
        # Must iterate to trigger ORM cascades (like deleting CryptoWallet orphans)
        investments_to_delete = self.db.query(Investment).filter(
            Investment.user_id == self.user_id,
            Investment.platform == platform_name
        ).all()
        
        for inv in investments_to_delete:
            self.db.delete(inv)
        
        # 3. Remove color preference (optional clean up)
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if user and user.preferences:
            prefs = dict(user.preferences)
            colors = prefs.get('platform_colors', {})
            if platform_name in colors:
                del colors[platform_name]
                prefs['platform_colors'] = colors
                user.preferences = prefs
                flag_modified(user, "preferences")
        
        self.db.commit()
        return {"status": "success", "platform": platform_name}
    
    
    # Default colors matching Web App Tailwind classes
    DEFAULT_PLATFORM_COLORS = {
        'Degiro': '#2563EB',         # bg-blue-600
        'Trading212 ISA': '#10B981', # bg-emerald-500
        'Trading212 GIA': '#3B82F6', # bg-blue-500
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
        
        investments = self.db.query(Investment).filter(
            Investment.user_id == self.user_id,
            ~Investment.platform.in_(self.TRADING212_PLATFORMS.values()),
        ).all()
        
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
        """
        Update live prices for all investments asynchronously.
        InvestEngine holdings use 'previous_close' to align with their app.
        Others use 'live' prices.
        """
        from app.utils.price_fetcher import PriceFetcher
        import logging
        logger = logging.getLogger(__name__)
        
        price_fetcher = PriceFetcher()
        
        investments = self.db.query(Investment).filter(
            Investment.user_id == self.user_id,
            ~Investment.platform.in_(self.TRADING212_PLATFORMS.values()),
        ).all()
        
        # Split investments
        investengine_investments = [inv for inv in investments if inv.platform == 'InvestEngine ISA']
        standard_investments = [inv for inv in investments if inv.platform != 'InvestEngine ISA']
        
        investengine_symbols = list(set([inv.symbol for inv in investengine_investments if inv.symbol]))
        standard_symbols = list(set([inv.symbol for inv in standard_investments if inv.symbol]))
        
        updated_count = 0
        
        # 1. Fetch Standard (Live)
        prices_standard = {}
        if standard_symbols:
            logger.info(f"HoldingsService: Fetching LIVE prices for {len(standard_symbols)} symbols...")
            prices_standard = await price_fetcher.get_multiple_prices_async(standard_symbols, use_previous_close=False)
            
        # 2. Fetch InvestEngine (Previous Close)
        prices_investengine = {}
        if investengine_symbols:
            logger.info(f"HoldingsService: Fetching PREV CLOSE prices for {len(investengine_symbols)} InvestEngine symbols...")
            prices_investengine = await price_fetcher.get_multiple_prices_async(investengine_symbols, use_previous_close=True)
            
        # 3. Update Investments
        
        # Standard
        for investment in standard_investments:
             if investment.symbol and investment.symbol in prices_standard:
                 investment.current_price = prices_standard[investment.symbol]
                 investment.last_updated = datetime.now()
                 updated_count += 1
        
        # InvestEngine
        for investment in investengine_investments:
             if investment.symbol and investment.symbol in prices_investengine:
                 investment.current_price = prices_investengine[investment.symbol]
                 investment.last_updated = datetime.now()
                 updated_count += 1
                
        self.db.commit()
        
        # 4. Check for staleness
        from datetime import timedelta
        stale_threshold = datetime.now() - timedelta(hours=24)
        stale_count = 0
        for investment in investments:
             if investment.symbol and investment.last_updated and investment.last_updated < stale_threshold:
                  stale_count += 1
                  logger.warning(f"HoldingsService: Price for {investment.symbol} ({investment.name}) is stale (last updated {investment.last_updated})")
                  
        logger.info(f"HoldingsService: Updated {updated_count} investments (Std: {len(prices_standard)}, IE: {len(prices_investengine)}). Stale: {stale_count}")
        return {"status": "success", "updated_count": updated_count, "stale_count": stale_count}
                
    
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

    @staticmethod
    def _normalize_trading212_uk_prices(
        current_price: float,
        average_price: float,
        currency: str,
        is_london_instrument: bool,
    ) -> tuple[float, float]:
        """Return GBP prices when Trading 212 mixes pounds and pence.

        The legacy endpoint can omit currency and, for some London instruments,
        return currentPrice in pence while averagePrice is already in pounds.
        Comparing the two prices lets us correct that mixed-unit response without
        hard-coding individual tickers.
        """
        normalized_currency = currency.upper()
        if normalized_currency in {'GBX', 'GBPENCE'}:
            return current_price / 100.0, average_price / 100.0

        if normalized_currency != 'GBP' and not is_london_instrument:
            return current_price, average_price

        if current_price > 0 and average_price > 0:
            current_to_average = current_price / average_price
            average_to_current = average_price / current_price
            if 50.0 <= current_to_average <= 150.0:
                return current_price / 100.0, average_price
            if 50.0 <= average_to_current <= 150.0:
                return current_price, average_price / 100.0

        # With no currency metadata, two similar large London prices are most
        # likely both pence (for example 1,372p and 1,186p).
        if (
            not normalized_currency
            and is_london_instrument
            and current_price > 500.0
            and average_price > 500.0
        ):
            return current_price / 100.0, average_price / 100.0

        return current_price, average_price

    @staticmethod
    def _validate_trading212_totals(
        account_summary: Dict[str, Any],
        positions_value: float,
        cash_balance: float,
    ) -> None:
        """Reject a sync whose normalized values disagree with Trading 212."""
        investments_summary = account_summary.get('investments') or {}
        expected_positions = investments_summary.get('currentValue')
        expected_total = account_summary.get('totalValue')

        if expected_positions is None and expected_total is not None:
            expected_positions = float(expected_total) - cash_balance

        comparisons = []
        if expected_positions is not None:
            comparisons.append(
                ('investment value', positions_value, float(expected_positions))
            )
        if expected_total is not None:
            comparisons.append(
                ('account value', positions_value + cash_balance, float(expected_total))
            )

        for label, calculated, expected in comparisons:
            tolerance = max(2.0, abs(expected) * 0.02)
            if abs(calculated - expected) > tolerance:
                raise ValueError(
                    f"Trading 212 {label} validation failed: calculated "
                    f"£{calculated:,.2f}, account reports £{expected:,.2f}. "
                    "The previous saved values were kept."
                )

    async def sync_trading212_investments(
        self,
        api_key_id: str,
        api_secret_key: str,
        account_type: str = 'isa',
        account_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Sync one account-scoped Trading 212 connection into its platform."""
        from app.services.trading212_service import Trading212Service
        from app.utils.price_fetcher import PriceFetcher
        import logging
        logger = logging.getLogger(__name__)

        account_type = account_type.strip().lower()
        target_platform = self.TRADING212_PLATFORMS.get(account_type)
        if not target_platform:
            raise ValueError("Trading 212 account type must be 'isa' or 'gia'")

        logger.info(f"T212 Sync: Starting {target_platform} upsert sync...")
        t212 = Trading212Service(api_key_id, api_secret_key)
        loop = asyncio.get_running_loop()
        portfolio = await loop.run_in_executor(None, t212.fetch_portfolio)

        if account_summary is None:
            try:
                account_summary = await loop.run_in_executor(None, t212.fetch_account_summary)
            except ValueError:
                # The existing ISA integration predates account-summary syncing. Keep it
                # operational if its old key lacks Account Data permission, while GIA
                # requires the summary so cash-only accounts still appear correctly.
                if account_type == 'gia':
                    raise
                logger.warning(
                    "T212 Sync: ISA account summary unavailable; continuing with positions only"
                )

        logger.info(
            f"T212 Sync: Fetched {len(portfolio)} {target_platform} positions"
        )

        # The current Positions API already gives exact account-currency values.
        # Only call the FX service for legacy USD positions that lack walletImpact.
        requires_usd_fx = any(
            not (
                item.get('_source') == 'positions'
                and
                (item.get('walletImpact') or {}).get('currentValue') is not None
                and (item.get('walletImpact') or {}).get('totalCost') is not None
            )
            and (
                str(item.get('currency', '')).upper() == 'USD'
                or str(item.get('ticker', '')).endswith('_US_EQ')
            )
            for item in portfolio
        )
        price_fetcher = PriceFetcher()

        usd_to_gbp = price_fetcher.get_usd_to_gbp_rate() if requires_usd_fx else 1.0
        if requires_usd_fx:
            logger.info(f"T212 Sync: USD to GBP rate: {usd_to_gbp}")

        # Normalize the complete response in memory. No database row is touched
        # until every position has been checked against the account summary.
        normalized_positions = []
        synced_positions_value = 0.0

        for item in portfolio:
            raw_ticker = item.get('ticker', '')
            quantity = float(item.get('quantity', 0))
            avg_price = float(item.get('averagePrice', 0))
            current_price = float(item.get('currentPrice', 0))
            currency = str(item.get('currency') or '').upper()

            normalized_symbol = self.normalize_trading212_ticker(raw_ticker)
            final_symbol = self.remap_ticker(normalized_symbol)
            fallback_name = item.get('name') or final_symbol
            company_name = self.get_company_name_safe(final_symbol, fallback_name)

            if not currency and raw_ticker.endswith('_US_EQ'):
                currency = 'USD'

            wallet_impact = item.get('walletImpact') or {}
            has_exact_wallet_values = (
                item.get('_source') == 'positions'
                and wallet_impact.get('currentValue') is not None
                and wallet_impact.get('totalCost') is not None
            )

            if has_exact_wallet_values:
                current_position_value = float(wallet_impact['currentValue'])
                target_amount_spent = float(wallet_impact['totalCost'])
                if quantity > 0:
                    current_price = current_position_value / quantity
                    avg_price = target_amount_spent / quantity
            if currency == 'USD':
                if not has_exact_wallet_values and quantity > 0 and current_price > 0:
                    current_price *= usd_to_gbp
                    current_position_value = quantity * current_price
                    target_amount_spent = current_position_value - float(item.get('ppl', 0))
                    avg_price = target_amount_spent / quantity
                elif not has_exact_wallet_values:
                    current_price *= usd_to_gbp
                    avg_price *= usd_to_gbp
                    current_position_value = quantity * current_price
                    target_amount_spent = quantity * avg_price
            elif not has_exact_wallet_values:
                current_price, avg_price = self._normalize_trading212_uk_prices(
                    current_price,
                    avg_price,
                    currency,
                    final_symbol.endswith('.L'),
                )
                current_position_value = quantity * current_price
                target_amount_spent = quantity * avg_price
            else:
                # Exact wallet values have already supplied account-currency
                # current value and cost, regardless of instrument currency.
                pass

            if quantity < 0 or current_position_value < 0 or target_amount_spent < 0:
                raise ValueError(
                    f"Trading 212 returned invalid values for {final_symbol}; "
                    "the previous saved values were kept."
                )

            synced_positions_value += current_position_value
            normalized_positions.append({
                'symbol': final_symbol,
                'name': company_name,
                'holdings': quantity,
                'average_buy_price': avg_price,
                'amount_spent': target_amount_spent,
                'current_price': current_price,
            })

        # Work out cash before validation, but still do not mutate the database.
        cash_balance = None
        account_id = None
        if account_summary:
            account_id = str(account_summary['id'])
            cash_summary = account_summary.get('cash') or {}
            explicit_cash_values = [
                cash_summary.get('availableToTrade'),
                cash_summary.get('inPies'),
                cash_summary.get('reservedForOrders'),
            ]
            if any(value is not None for value in explicit_cash_values):
                cash_balance = sum(float(value or 0.0) for value in explicit_cash_values)
            else:
                account_total = float(account_summary.get('totalValue') or 0.0)
                cash_balance = max(account_total - synced_positions_value, 0.0)

            self._validate_trading212_totals(
                account_summary,
                synced_positions_value,
                cash_balance,
            )

        existing_investments = self.db.query(Investment).filter(
            Investment.user_id == self.user_id,
            Investment.platform == target_platform,
        ).all()
        existing_by_symbol = {
            investment.symbol: investment
            for investment in existing_investments
            if investment.symbol
        }
        logger.info(
            f"T212 Sync: Validated account totals; applying {len(normalized_positions)} "
            f"positions over {len(existing_investments)} existing rows"
        )

        incoming_symbols = {position['symbol'] for position in normalized_positions}
        added_count = 0
        updated_count = 0
        unchanged_count = 0
        deleted_count = 0

        try:
            for position in normalized_positions:
                existing = existing_by_symbol.get(position['symbol'])
                if existing:
                    changed = (
                        abs(existing.holdings - position['holdings']) > 0.0001
                        or abs(existing.amount_spent - position['amount_spent']) > 0.01
                        or abs(existing.current_price - position['current_price']) > 0.0001
                        or existing.name != position['name']
                    )
                    if changed:
                        existing.holdings = position['holdings']
                        existing.average_buy_price = position['average_buy_price']
                        existing.amount_spent = position['amount_spent']
                        existing.current_price = position['current_price']
                        existing.name = position['name']
                        existing.last_updated = datetime.utcnow()
                        updated_count += 1
                    else:
                        unchanged_count += 1
                else:
                    self.db.add(Investment(
                        user_id=self.user_id,
                        platform=target_platform,
                        name=position['name'],
                        symbol=position['symbol'],
                        holdings=position['holdings'],
                        average_buy_price=position['average_buy_price'],
                        amount_spent=position['amount_spent'],
                        current_price=position['current_price'],
                    ))
                    added_count += 1

            for symbol, investment in existing_by_symbol.items():
                if symbol not in incoming_symbols:
                    self.db.delete(investment)
                    deleted_count += 1

            if cash_balance is not None:
                cash_entry = self.db.query(PlatformCash).filter(
                    PlatformCash.user_id == self.user_id,
                    PlatformCash.platform == target_platform,
                ).first()
                if cash_entry:
                    cash_entry.cash_balance = cash_balance
                    cash_entry.last_updated = datetime.utcnow()
                else:
                    self.db.add(PlatformCash(
                        user_id=self.user_id,
                        platform=target_platform,
                        cash_balance=cash_balance,
                    ))

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        
        logger.info(
            f"T212 Sync: Complete. "
            f"Added={added_count}, Updated={updated_count}, "
            f"Unchanged={unchanged_count}, Deleted={deleted_count}"
        )
        
        return {
            "status": "success",
            "message": f"Synced {len(portfolio)} positions into {target_platform}",
            "platform": target_platform,
            "account_type": account_type,
            "account_id": account_id,
            "cash_balance": cash_balance,
            "added": added_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
            "deleted": deleted_count
        }

    def save_trading212_credentials(
        self,
        api_key_id: str,
        api_secret_key: str,
        account_type: str = 'isa',
        account_id: Optional[str] = None,
    ) -> bool:
        """Encrypt and save one account-scoped Trading 212 connection."""
        from app.utils.security import encrypt_value
        from app.models import User
        from sqlalchemy.orm.attributes import flag_modified
        import logging
        logger = logging.getLogger(__name__)
        
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user:
            logger.error(f"T212 Save: User {self.user_id} not found")
            return False
        
        account_type = account_type.strip().lower()
        platform = self.TRADING212_PLATFORMS.get(account_type)
        if not platform:
            raise ValueError("Trading 212 account type must be 'isa' or 'gia'")

        prefs = dict(user.preferences) if user.preferences else {}
        t212_config = {
            "enabled": True,
            "account_type": account_type,
            "platform": platform,
            "account_id": str(account_id) if account_id is not None else None,
            "api_key_id_enc": encrypt_value(api_key_id),
            "api_secret_key_enc": encrypt_value(api_secret_key),
            "updated_at": datetime.utcnow().isoformat()
        }

        accounts = dict(prefs.get('trading212_accounts') or {})
        accounts[account_type] = t212_config
        prefs['trading212_accounts'] = accounts

        # Keep the original ISA slot updated so rolling back this release cannot
        # disable the established ISA auto-sync.
        if account_type == 'isa':
            prefs['trading212_sync'] = t212_config

        user.preferences = prefs
        flag_modified(user, "preferences")
        
        self.db.commit()
        logger.info(f"T212 Save: {platform} credentials saved for user {self.user_id}")
        return True

    def get_trading212_credentials(
        self,
        account_type: str = 'isa',
    ) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt one Trading 212 connection."""
        from app.utils.security import decrypt_value
        from app.models import User
        import logging
        logger = logging.getLogger(__name__)
        
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user or not user.preferences:
            logger.debug(f"T212 Creds: User {self.user_id} has no preferences")
            return None
        
        account_type = account_type.strip().lower()
        platform = self.TRADING212_PLATFORMS.get(account_type)
        if not platform:
            return None

        prefs = user.preferences
        accounts = prefs.get('trading212_accounts') or {}
        t212_config = accounts.get(account_type)

        # Backward compatibility: production currently stores the ISA here.
        if not t212_config and account_type == 'isa':
            t212_config = prefs.get('trading212_sync')
        
        if not t212_config:
            logger.debug("T212 Creds: No trading212_sync config found")
            return None
        if not t212_config.get('enabled'):
            logger.debug("T212 Creds: Auto-sync is disabled")
            return None
            
        try:
            return {
                "api_key_id": decrypt_value(t212_config.get('api_key_id_enc')),
                "api_secret_key": decrypt_value(t212_config.get('api_secret_key_enc')),
                "account_type": account_type,
                "platform": platform,
                "account_id": t212_config.get('account_id'),
                "updated_at": t212_config.get('updated_at'),
            }
        except Exception as e:
            logger.error(f"T212 Creds: Decryption failed: {e}")
            return None

    def get_trading212_connections(self) -> List[Dict[str, Any]]:
        """Return every enabled Trading 212 account without lumping them together."""
        connections = []
        for account_type in self.TRADING212_PLATFORMS:
            credentials = self.get_trading212_credentials(account_type)
            if credentials:
                connections.append(credentials)
        return connections
