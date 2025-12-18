from sqlalchemy.orm import Session
from app.models import MonthlyFinancialRecord, NetWorthSnapshot
from app.services.holdings_service import HoldingsService
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
import calendar

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

    def _parse_month(self, month_str: str) -> int:
        """Helper to parse month string like 'January', 'Jan', '1st Jan' to 1-12"""
        month_str = month_str.replace("1st ", "").strip()
        month_map = {m: i for i, m in enumerate(calendar.month_abbr) if i}
        full_month_map = {m: i for i, m in enumerate(calendar.month_name) if i}
        
        if month_str in month_map:
            return month_map[month_str]
        if month_str in full_month_map:
            return full_month_map[month_str]
        
        # Fallback/Edge cases from legacy data
        legacy_map = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
            '31st Dec': 12 # Treat as Dec
        }
        if "31st Dec" in month_str:
            return 12
            
        return legacy_map.get(month_str, datetime.now().month)

    def get_networth_history(self, year: Optional[int] = None, months: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get networth data history."""
        
        # If specific year requested, query MonthlyFinancialRecord
        if year:
            records = self.db.query(MonthlyFinancialRecord).filter(
                MonthlyFinancialRecord.user_id == self.user_id,
                MonthlyFinancialRecord.period_date >= date(year, 1, 1),
                MonthlyFinancialRecord.period_date <= date(year, 12, 31)
            ).order_by(MonthlyFinancialRecord.period_date.asc()).all()
            
            return [{
                "date": r.period_date.strftime("%Y-%m-%d"),
                "value": r.net_worth,
                "platform_breakdown": r.details
            } for r in records]

        # If recent months requested (e.g. for chart daily view)
        if months:
            start_date = datetime.utcnow() - timedelta(days=months*30)
            snapshots = self.db.query(NetWorthSnapshot).filter(
                NetWorthSnapshot.user_id == self.user_id,
                NetWorthSnapshot.timestamp >= start_date
            ).order_by(NetWorthSnapshot.timestamp.asc()).all()
            
            # If no detailed snapshots, fallback to monthly records
            if not snapshots:
                records = self.db.query(MonthlyFinancialRecord).filter(
                    MonthlyFinancialRecord.user_id == self.user_id,
                    MonthlyFinancialRecord.period_date >= start_date.date()
                ).order_by(MonthlyFinancialRecord.period_date.asc()).all()
                return [{
                    "date": r.period_date.strftime("%Y-%m-%d"),
                    "value": r.net_worth,
                    "platform_breakdown": r.details
                } for r in records]

            return [{
                "date": s.timestamp.isoformat(),
                "value": s.total_amount,
                "platform_breakdown": s.assets_breakdown
            } for s in snapshots]

        # Default all time monthly
        records = self.db.query(MonthlyFinancialRecord).filter(
            MonthlyFinancialRecord.user_id == self.user_id
        ).order_by(MonthlyFinancialRecord.period_date.asc()).all()
        
        return [{
            "date": r.period_date.strftime("%Y-%m-%d"),
            "value": r.net_worth,
            "platform_breakdown": r.details
        } for r in records]

    def save_networth_snapshot(self, year: int, month: str):
        """
        Take a snapshot of current net worth and save it as a MonthlyFinancialRecord.
        Typically called "saving month end" or "starting month".
        """
        platform_totals = self.calculate_platform_totals()
        total_networth = sum(platform_totals.values())
        
        month_num = self._parse_month(month)
        
        # We store it as the 1st of the month
        period_date = date(year, month_num, 1)
        
        record = self.db.query(MonthlyFinancialRecord).filter(
            MonthlyFinancialRecord.user_id == self.user_id,
            MonthlyFinancialRecord.period_date == period_date
        ).first()
        
        if record:
            record.details = platform_totals
            record.net_worth = total_networth
        else:
            record = MonthlyFinancialRecord(
                user_id=self.user_id,
                period_date=period_date,
                net_worth=total_networth,
                details=platform_totals
            )
            self.db.add(record)
        
        self.db.commit()
        return record

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get summary for the home page:
        - Total Net Worth
        - This Month Change (vs start of month)
        - This Year Change (vs start of year)
        - Platform Breakdown with Monthly Change
        """
        current_date = date.today()
        current_month_start = date(current_date.year, current_date.month, 1)
        current_year_start = date(current_date.year, 1, 1)
        
        # 1. Current Net Worth & Platform Totals
        platform_totals = self.calculate_platform_totals()
        total_networth = sum(platform_totals.values())
        
        # 2. Get comparative data points
        # Start of Current Month Record
        month_start_record = self.db.query(MonthlyFinancialRecord).filter(
            MonthlyFinancialRecord.user_id == self.user_id,
            MonthlyFinancialRecord.period_date == current_month_start
        ).first()
        
        # Start of Year Record
        year_start_record = self.db.query(MonthlyFinancialRecord).filter(
            MonthlyFinancialRecord.user_id == self.user_id,
            MonthlyFinancialRecord.period_date == current_year_start
        ).first()
        
        # 3. Calculate Month Change
        month_change_amount = 0.0
        month_change_percent = 0.0
        month_start_platform_data = {}
        
        if month_start_record:
            month_start_total = month_start_record.net_worth
            month_start_platform_data = month_start_record.details or {}
            if month_start_total > 0:
                month_change_amount = total_networth - month_start_total
                month_change_percent = (month_change_amount / month_start_total) * 100
        
        # 4. Calculate Year Change
        year_change_amount = 0.0
        year_change_percent = 0.0
        
        if year_start_record:
            year_start_total = year_start_record.net_worth
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
            "platform_breakdown": platform_totals,
            "platforms": platforms_summary
        }

    def get_monthly_tracker_data(self) -> List[Dict[str, Any]]:
        """
        Get data for the Month/Year tracker page.
        Returns list of monthly snapshots with MoM differences.
        """
        records = self.db.query(MonthlyFinancialRecord).filter(
            MonthlyFinancialRecord.user_id == self.user_id
        ).order_by(MonthlyFinancialRecord.period_date.desc()).all()
        
        result = []
        for i, record in enumerate(records):
            # Calculate difference from previous month (next item in list since desc sort)
            prev_record = records[i+1] if i + 1 < len(records) else None
            
            diff_amount = 0.0
            diff_percent = 0.0
            
            if prev_record and prev_record.net_worth > 0:
                diff_amount = record.net_worth - prev_record.net_worth
                diff_percent = (diff_amount / prev_record.net_worth) * 100
            
            # Legacy format support for frontend: year, month string
            # We can convert date back to legacy format "Jan", "Feb" etc
            # Frontend matches "1st Jan", "1st Feb" etc.
            month_name = f"1st {record.period_date.strftime('%b')}"
            
            result.append({
                "year": record.period_date.year,
                "month": month_name,
                "total_networth": record.net_worth,
                "platform_breakdown": record.details,
                "mom_change_amount": diff_amount,
                "mom_change_percent": diff_percent
            })
            
        return result

    def save_intraday_snapshot(self):
        """Save a high-frequency snapshot of the current net worth"""
        platform_totals = self.calculate_platform_totals()
        total_networth = sum(platform_totals.values())
        
        snapshot = NetWorthSnapshot(
            user_id=self.user_id,
            timestamp=datetime.utcnow(),
            total_amount=total_networth,
            assets_breakdown=platform_totals
        )
        self.db.add(snapshot)
        self.db.commit()
        return snapshot

    def get_graph_data(self, period: str) -> List[Dict[str, Any]]:
        """
        Get graph data based on period.
        Tiered Strategy:
        - 24H, 1W: NetWorthSnapshot (High frequency)
        - 1M, 3M: NetWorthSnapshot (High frequency, maybe sampled)
        - 6M, 1Y, MAX: MonthlyFinancialRecord (Low frequency)
        """
        period = period.upper() if period else '1Y'
        now = datetime.utcnow()
        
        # --- High Frequency / Intraday DB Source ---
        if period in ['24H', '1W', '1M', '3M']:
            hours_lookback = 24
            if period == '1W': hours_lookback = 168
            elif period == '1M': hours_lookback = 720
            elif period == '3M': hours_lookback = 2160
            
            start_time = now - timedelta(hours=hours_lookback)
            
            snapshots = self.db.query(NetWorthSnapshot).filter(
                NetWorthSnapshot.user_id == self.user_id,
                NetWorthSnapshot.timestamp >= start_time
            ).order_by(NetWorthSnapshot.timestamp.asc()).all()
            
            data = [{
                "date": s.timestamp.isoformat(),
                "value": s.total_amount,
                "platform_breakdown": s.assets_breakdown
            } for s in snapshots]
            
            # Sampling for longer periods to prevent sending too much data
            # 1W: ~6h
            # 1M: ~1d
            # 3M: ~1d
            if period == '1W' and len(data) > 40:
                data = self._sample_data(data, timedelta(hours=6))
            elif period in ['1M', '3M'] and len(data) > 60:
                data = self._sample_data(data, timedelta(days=1))
                
            return data

        # --- Low Frequency / Monthly DB Source ---
        # 6M, 1Y, MAX
        months_lookback = 12 # Default 1Y
        if period == '6M': months_lookback = 6
        elif period == 'MAX': months_lookback = 1200 # 100 years
        
        start_date = (now - timedelta(days=months_lookback * 30)).date()
        
        records = self.db.query(MonthlyFinancialRecord).filter(
            MonthlyFinancialRecord.user_id == self.user_id,
            MonthlyFinancialRecord.period_date >= start_date
        ).order_by(MonthlyFinancialRecord.period_date.asc()).all()
        
        return [{
            "date": r.period_date.strftime("%Y-%m-%d"),
            "value": r.net_worth,
            "platform_breakdown": r.details
        } for r in records]

    def _sample_data(self, data: List[Dict], interval: timedelta) -> List[Dict]:
        """Helper to sample time series data"""
        if not data: return []
        
        sampled = []
        last_time = None
        
        for point in data:
            pt_time = datetime.fromisoformat(point['date'])
            if last_time is None or (pt_time - last_time) >= interval:
                sampled.append(point)
                last_time = pt_time
                
        # Always include latest point
        if data[-1] not in sampled:
            sampled.append(data[-1])
            
        return sampled
