from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from app.database import get_db
from app.dependencies import get_current_user_id
from app.services.holdings_service import HoldingsService
from app.schemas import Investment, InvestmentCreate, InvestmentUpdate, PlatformCash, PlatformCashUpdate

router = APIRouter(
    prefix="/holdings",
    tags=["holdings"]
)

@router.get("/", response_model=Dict[str, List[Investment]])
def get_holdings(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = HoldingsService(db, user_id)
    return service.get_investments_by_platform()

@router.post("/", response_model=Investment)
def add_investment(
    investment: InvestmentCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = HoldingsService(db, user_id)
    return service.add_investment(investment.platform, investment)

@router.put("/{investment_id}", response_model=Investment)
def update_investment(
    investment_id: int,
    updates: InvestmentUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = HoldingsService(db, user_id)
    try:
        updated = service.update_investment(investment_id, updates.dict(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Investment not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{investment_id}")
def delete_investment(
    investment_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = HoldingsService(db, user_id)
    try:
        service.delete_investment(investment_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/cash/{platform}", response_model=PlatformCash)
def get_platform_cash(
    platform: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = HoldingsService(db, user_id)
    balance = service.get_platform_cash(platform)
    return PlatformCash(platform=platform, cash_balance=balance)

@router.post("/cash/{platform}", response_model=PlatformCash)
def update_platform_cash(
    platform: str,
    cash_data: PlatformCashUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = HoldingsService(db, user_id)
    return service.update_platform_cash(platform, cash_data.cash_balance)

@router.post("/platform/rename")
def rename_platform(
    old_name: str,
    new_name: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = HoldingsService(db, user_id)
    return service.rename_platform(old_name, new_name)

@router.post("/platform/color")
def update_platform_color(
    platform: str,
    color: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = HoldingsService(db, user_id)
    return service.update_platform_color(platform, color)

@router.get("/platform/colors")
def get_platform_colors(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = HoldingsService(db, user_id)
    return service.get_platform_colors()

@router.post("/refresh-prices")
async def refresh_prices(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Update current prices for all investments with symbols using robust PriceFetcher"""
    holdings_service = HoldingsService(db, user_id)
    return await holdings_service.update_all_prices_async()

from pydantic import BaseModel

class Trading212ImportRequest(BaseModel):
    api_key_id: str
    api_secret_key: str
    save_credentials: bool = False

@router.post("/import/trading212")
async def import_trading212(
    request: Trading212ImportRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Import investments from Trading212"""
    holdings_service = HoldingsService(db, user_id)
    try:
        # Save if requested
        if request.save_credentials:
            holdings_service.save_trading212_credentials(request.api_key_id, request.api_secret_key)
            
        # Pass both keys for robust auth
        return await holdings_service.sync_trading212_investments(request.api_key_id, request.api_secret_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class T212Config(BaseModel):
    api_key_id: str
    api_secret_key: str

@router.post("/config/trading212")
def save_trading212_config(
    config: T212Config,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Save Trading212 API credentials securely"""
    holdings_service = HoldingsService(db, user_id)
    success = holdings_service.save_trading212_credentials(config.api_key_id, config.api_secret_key)
    return {"status": "success" if success else "error"}

@router.get("/config/trading212")
def get_trading212_config(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Check if T212 auto-sync is enabled"""
    holdings_service = HoldingsService(db, user_id)
    creds = holdings_service.get_trading212_credentials()
    return {"enabled": creds is not None}
