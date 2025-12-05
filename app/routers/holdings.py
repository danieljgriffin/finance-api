from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from app.database import get_db
from app.dependencies import get_current_user_id
from app.services.holdings_service import HoldingsService
from app.services.price_service import PriceService
from app.schemas import Investment, InvestmentCreate, PlatformCash

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
    amount: float,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = HoldingsService(db, user_id)
    return service.update_platform_cash(platform, amount)

@router.post("/refresh-prices")
def refresh_prices(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Update current prices for all investments with symbols"""
    holdings_service = HoldingsService(db, user_id)
    price_service = PriceService()
    
    investments_data = holdings_service.get_investments_by_platform()
    updated_count = 0
    
    for platform, investments in investments_data.items():
        for inv in investments:
            symbol = inv.get('symbol')
            if symbol:
                price = price_service.get_price(symbol)
                if price:
                    holdings_service.update_investment(inv['id'], {'current_price': price})
                    updated_count += 1
                    
    return {"status": "success", "updated_count": updated_count}
