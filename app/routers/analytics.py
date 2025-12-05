from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.dependencies import get_current_user_id
from app.services.analytics_service import AnalyticsService

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"]
)

@router.get("/timeseries")
def get_timeseries(
    range: str = '1m',
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get historical data for the graph.
    Range options: 24h, 1w, 1m, 3m, 6m, 1y, max
    """
    service = AnalyticsService(db, user_id)
    return service.get_timeseries(range)

@router.post("/capture")
def capture_snapshot(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Trigger a historical data capture (for 15-min intervals).
    Should be called by an external scheduler.
    """
    service = AnalyticsService(db, user_id)
    entry = service.capture_snapshot()
    return {
        "status": "success", 
        "timestamp": entry.timestamp.isoformat(),
        "net_worth": entry.net_worth
    }

@router.post("/cleanup")
def cleanup_history(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Trigger cleanup of old historical data.
    Should be called periodically (e.g., daily).
    """
    service = AnalyticsService(db, user_id)
    service.cleanup_history()
    return {"status": "success"}
