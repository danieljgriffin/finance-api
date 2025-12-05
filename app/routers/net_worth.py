from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.dependencies import get_current_user_id
from app.services.net_worth_service import NetWorthService

router = APIRouter(
    prefix="/net-worth",
    tags=["net-worth"]
)

@router.get("/summary")
def get_net_worth_summary(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = NetWorthService(db, user_id)
    platform_totals = service.calculate_platform_totals()
    total_networth = sum(platform_totals.values())
    
    return {
        "total_networth": total_networth,
        "platform_breakdown": platform_totals
    }

@router.get("/history/{year}")
def get_networth_history(
    year: str, # changed to str to accept "all" or specific year
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = NetWorthService(db, user_id)
    if year.lower() == "all":
        return service.get_networth_history(None)
    return service.get_networth_history(int(year))

@router.post("/snapshot")
def create_snapshot(
    year: int,
    month: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = NetWorthService(db, user_id)
    entry = service.save_networth_snapshot(year, month)
    return {"status": "success", "total_networth": entry.total_networth}

@router.get("/dashboard-summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = NetWorthService(db, user_id)
    data = service.get_dashboard_summary()
    
    # Transform to match frontend expectation
    return {
        "total_networth": data["total_networth"],
        "mom_change": data["month_change"]["amount"],
        "mom_change_percent": data["month_change"]["percent"],
        "ytd_change": data["year_change"]["amount"],
        "ytd_change_percent": data["year_change"]["percent"],
        "platforms": data["platforms"]
    }

@router.get("/monthly-tracker")
def get_monthly_tracker(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = NetWorthService(db, user_id)
    return service.get_monthly_tracker_data()

@router.post("/snapshot/intraday")
def create_intraday_snapshot(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Trigger a high-frequency snapshot"""
    service = NetWorthService(db, user_id)
    entry = service.save_intraday_snapshot()
    return {"status": "success", "timestamp": entry.timestamp, "value": entry.net_worth}

@router.get("/history/intraday/{hours}")
def get_intraday_history(
    hours: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = NetWorthService(db, user_id)
    return service.get_intraday_history(hours)
