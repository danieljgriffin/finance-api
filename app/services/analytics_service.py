from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import NetWorthSnapshot
from app.services.net_worth_service import NetWorthService
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.net_worth_service = NetWorthService(db, user_id)

    def capture_snapshot(self) -> NetWorthSnapshot:
        """
        Capture current net worth and platform breakdown for historical tracking.
        Should be called every 15 minutes by a scheduler.
        """
        # Calculate current net worth and platform breakdown
        platform_totals = self.net_worth_service.calculate_platform_totals()
        current_net_worth = sum(platform_totals.values())
        
        # Store historical data point
        snapshot = NetWorthSnapshot(
            user_id=self.user_id,
            timestamp=datetime.utcnow(),
            total_amount=current_net_worth,
            assets_breakdown=platform_totals
        )
        
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        
        return snapshot

    def sample_data_by_interval(self, data_list: List[NetWorthSnapshot], hours: int) -> List[NetWorthSnapshot]:
        """Sample historical data to get roughly one point per interval"""
        if not data_list:
            return []
        
        sampled_data = []
        last_sampled_time = None
        interval = timedelta(hours=hours)
        
        for data_point in data_list:
            if last_sampled_time is None or (data_point.timestamp - last_sampled_time) >= interval:
                sampled_data.append(data_point)
                last_sampled_time = data_point.timestamp
        
        # Always include the last data point
        if data_list and data_list[-1] not in sampled_data:
            sampled_data.append(data_list[-1])
        
        return sampled_data

    def cleanup_history(self):
        """
        Clean up old high-frequency data based on tiered retention policy.
        - < 24h: Keep all (15 min intervals)
        - 24h - 7d: Keep 6h intervals
        - > 7d: Keep 12h intervals
        """
        now = datetime.utcnow()
        cutoff_24h = now - timedelta(days=1)
        cutoff_7d = now - timedelta(days=7)
        
        # 1. Process 24h - 7d window
        recent_old_data = self.db.query(NetWorthSnapshot).filter(
            NetWorthSnapshot.user_id == self.user_id,
            NetWorthSnapshot.timestamp < cutoff_24h,
            NetWorthSnapshot.timestamp >= cutoff_7d
        ).order_by(NetWorthSnapshot.timestamp.asc()).all()
        
        if recent_old_data:
            to_keep = self.sample_data_by_interval(recent_old_data, hours=6)
            to_keep_ids = [item.id for item in to_keep]
            
            # Delete the rest in this window
            self.db.query(NetWorthSnapshot).filter(
                NetWorthSnapshot.user_id == self.user_id,
                NetWorthSnapshot.timestamp < cutoff_24h,
                NetWorthSnapshot.timestamp >= cutoff_7d,
                ~NetWorthSnapshot.id.in_(to_keep_ids)
            ).delete(synchronize_session=False)
            
        # 2. Process > 7d window
        old_data = self.db.query(NetWorthSnapshot).filter(
            NetWorthSnapshot.user_id == self.user_id,
            NetWorthSnapshot.timestamp < cutoff_7d
        ).order_by(NetWorthSnapshot.timestamp.asc()).all()
        
        if old_data:
            to_keep = self.sample_data_by_interval(old_data, hours=12)
            to_keep_ids = [item.id for item in to_keep]
            
            # Delete the rest
            self.db.query(NetWorthSnapshot).filter(
                NetWorthSnapshot.user_id == self.user_id,
                NetWorthSnapshot.timestamp < cutoff_7d,
                ~NetWorthSnapshot.id.in_(to_keep_ids)
            ).delete(synchronize_session=False)
            
        self.db.commit()

    def get_timeseries(self, range_str: str = '1m') -> Dict[str, Any]:
        """
        Get historical data for the graph based on range.
        Ranges: 24h, 1w, 1m, 3m, 6m, 1y, max
        """
        now = datetime.utcnow()
        start_date = None
        
        if range_str == '24h':
            start_date = now - timedelta(days=1)
        elif range_str == '1w':
            start_date = now - timedelta(weeks=1)
        elif range_str == '1m':
            start_date = now - timedelta(days=30)
        elif range_str == '3m':
            start_date = now - timedelta(days=90)
        elif range_str == '6m':
            start_date = now - timedelta(days=180)
        elif range_str == '1y':
            start_date = now - timedelta(days=365)
        # 'max' leaves start_date as None
        
        query = self.db.query(NetWorthSnapshot).filter(
            NetWorthSnapshot.user_id == self.user_id
        )
        
        if start_date:
            query = query.filter(NetWorthSnapshot.timestamp >= start_date)
            
        data_points = query.order_by(NetWorthSnapshot.timestamp.asc()).all()
        
        # Format for frontend graph
        # Assuming frontend wants a list of {date, value} objects
        formatted_data = [
            {
                "date": point.timestamp.isoformat(),
                "value": point.total_amount,
                # Include platform breakdown if needed for stacked area charts?
                # "breakdown": point.assets_breakdown 
            }
            for point in data_points
        ]
        
        return {
            "range": range_str,
            "data": formatted_data
        }
