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
def get_net_worth_history(
    year: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = NetWorthService(db, user_id)
    return service.get_networth_history(year)

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
    return service.get_dashboard_summary()

@router.get("/monthly-tracker")
def get_monthly_tracker(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = NetWorthService(db, user_id)
    return service.get_monthly_tracker_data()
