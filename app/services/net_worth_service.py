from sqlalchemy.orm import Session
from app.models import NetworthEntry, HistoricalNetWorth
from app.services.holdings_service import HoldingsService
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

class NetWorthService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.holdings_service = HoldingsService(db, user_id)

    def calculate_platform_totals(self) -> Dict[str, float]:
        """Calculate total value for each platform - SINGLE SOURCE OF TRUTH"""
        investments_data = self.holdings_service.get_investments_by_platform()
        
        platform_totals = {}
        
        for platform, investments in investments_data.items():
            if platform.endswith('_cash'):
                continue  # Skip cash keys
                
            platform_total = 0.0
            
            # Calculate investment values (skip for Cash platform since it has no investments)
            if platform != 'Cash':
                platform_total = sum(
                    (inv.get('holdings', 0) or 0) * (inv.get('current_price', 0) or 0)
                    for inv in investments
                )
            
            # Add cash balance for this platform
            platform_total += self.holdings_service.get_platform_cash(platform)
            
            # Only include platforms with value
            if platform_total > 0:
                platform_totals[platform] = platform_total
        
        return platform_totals

    def calculate_current_net_worth(self) -> float:
        """Calculate current net worth by summing all platform totals"""
        platform_totals = self.calculate_platform_totals()
        return sum(platform_totals.values())

    def get_networth_history(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get networth data. If year is provided, filter by year. Else return all."""
        query = self.db.query(NetworthEntry).filter(
            NetworthEntry.user_id == self.user_id
        )
        
        if year:
            query = query.filter(NetworthEntry.year == year)
            
        entries = query.all()
        
        # Sort by month if possible, but month is a string name "Jan", "Feb" etc in DB? 
        # Ideally we convert to date. Assuming "1st Jan" format based on other snippets?
        # Let's clean this up.
        
        result = []
        for entry in entries:
            # parsing "1st Jan" or just "Jan"
            # For chart we likely want a comparable date string
            # Let's try to make a best effort ISO date string for standard parsing
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
                '31st Dec': 13 # Treat as month 13 for sorting purposes
            }
            # Handle "1st Jan" vs "Jan" vs "31st Dec"
            month_str = entry.month.replace("1st ", "")
            # If it was "31st Dec", the replace "1st " did nothing, so it remains "31st Dec".
            # If it was "1st Dec", it became "Dec".
            month_num = month_map.get(month_str, 1)
            
            # Construct a date string YYYY-MM-DD
            date_str = f"{year or entry.year}-{month_num:02d}-01"
            
            result.append({
                "date": date_str,
                "value": entry.total_networth,
                "platform_breakdown": entry.get_platform_data()
            })
            
        # Sort by date
        result.sort(key=lambda x: x['date'])
        
        return result

    def save_networth_snapshot(self, year: int, month: str):
        """Take a snapshot of current net worth and save it"""
        platform_totals = self.calculate_platform_totals()
        total_networth = sum(platform_totals.values())
        
        entry = self.db.query(NetworthEntry).filter(
            NetworthEntry.user_id == self.user_id,
            NetworthEntry.year == year,
            NetworthEntry.month == month
        ).first()
        
        if entry:
            entry.set_platform_data(platform_totals)
            entry.total_networth = total_networth
        else:
            entry = NetworthEntry(
                user_id=self.user_id,
                year=year,
                month=month,
                total_networth=total_networth
            )
            entry.set_platform_data(platform_totals)
            self.db.add(entry)
        
        self.db.commit()
        return entry

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get summary for the home page:
        - Total Net Worth
        - This Month Change (vs 1st of current month)
        - This Year Change (vs 1st Jan of current year)
        - Platform Breakdown with Monthly Change
        """
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # Month names mapping
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        current_month_name = f"1st {month_names[current_month - 1]}"
        
        # 1. Current Net Worth & Platform Totals
        platform_totals = self.calculate_platform_totals()
        total_networth = sum(platform_totals.values())
        
        # 2. Get comparative data points
        # 1st of Current Month
        month_start_entry = self.db.query(NetworthEntry).filter(
            NetworthEntry.user_id == self.user_id,
            NetworthEntry.year == current_year,
            NetworthEntry.month == current_month_name
        ).first()
        
        # 1st of Jan (Year Start)
        year_start_entry = self.db.query(NetworthEntry).filter(
            NetworthEntry.user_id == self.user_id,
            NetworthEntry.year == current_year,
            NetworthEntry.month == '1st Jan'
        ).first()
        
        # 3. Calculate Month Change
        month_change_amount = 0.0
        month_change_percent = 0.0
        month_start_platform_data = {}
        
        if month_start_entry:
            month_start_total = month_start_entry.total_networth
            month_start_platform_data = month_start_entry.get_platform_data()
            if month_start_total > 0:
                month_change_amount = total_networth - month_start_total
                month_change_percent = (month_change_amount / month_start_total) * 100
        
        # 4. Calculate Year Change
        year_change_amount = 0.0
        year_change_percent = 0.0
        
        if year_start_entry:
            year_start_total = year_start_entry.total_networth
            if year_start_total > 0:
                year_change_amount = total_networth - year_start_total
                year_change_percent = (year_change_amount / year_start_total) * 100
                
        # 5. Calculate Platform Monthly Changes
        platforms_summary = []
        for platform, value in platform_totals.items():
            prev_value = month_start_platform_data.get(platform, 0.0)
            change = value - prev_value
            percent = (change / prev_value * 100) if prev_value > 0 else 0.0
            
            platforms_summary.append({
                "platform": platform,
                "value": value,
                "month_change_amount": change,
                "month_change_percent": percent
            })
            
        return {
            "total_networth": total_networth,
            "month_change": {
                "amount": month_change_amount,
                "percent": month_change_percent
            },
            "year_change": {
                "amount": year_change_amount,
                "percent": year_change_percent
            },
            "platforms": platforms_summary
        }

    def get_monthly_tracker_data(self) -> List[Dict[str, Any]]:
        """
        Get data for the Month/Year tracker page.
        Returns list of monthly snapshots with MoM differences.
        """
        entries = self.db.query(NetworthEntry).filter(
            NetworthEntry.user_id == self.user_id
        ).order_by(NetworthEntry.year.desc(), NetworthEntry.id.desc()).all()
        
        # Sort logic to handle month names properly would be ideal here or in frontend
        # For now, returning raw entries, frontend can sort/process
        
        result = []
        for i, entry in enumerate(entries):
            # Calculate difference from previous month (next item in list since desc sort)
            prev_entry = entries[i+1] if i + 1 < len(entries) else None
            
            diff_amount = 0.0
            diff_percent = 0.0
            
            if prev_entry and prev_entry.total_networth > 0:
                diff_amount = entry.total_networth - prev_entry.total_networth
                diff_percent = (diff_amount / prev_entry.total_networth) * 100
                
            result.append({
                "year": entry.year,
                "month": entry.month,
                "total_networth": entry.total_networth,
                "platform_breakdown": entry.get_platform_data(),
                "mom_change_amount": diff_amount,
                "mom_change_percent": diff_percent
            })
            
        return result

    def save_intraday_snapshot(self):
        """Save a high-frequency snapshot of the current net worth"""
        platform_totals = self.calculate_platform_totals()
        total_networth = sum(platform_totals.values())
        
        entry = HistoricalNetWorth(
            user_id=self.user_id,
            timestamp=datetime.utcnow(),
            net_worth=total_networth,
            platform_breakdown=platform_totals
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def get_intraday_history(self, hours: int) -> List[Dict[str, Any]]:
        """Get granular history for the last N hours"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        entries = self.db.query(HistoricalNetWorth).filter(
            HistoricalNetWorth.user_id == self.user_id,
            HistoricalNetWorth.timestamp >= start_time
        ).order_by(HistoricalNetWorth.timestamp.asc()).all()
        
        return [{
            "date": entry.timestamp.isoformat(),
            "value": entry.net_worth,
            "platform_breakdown": entry.platform_breakdown
        } for entry in entries]
