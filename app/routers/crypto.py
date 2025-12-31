from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.crypto_service import CryptoService
from app.services.holdings_service import HoldingsService
from app.schemas import InvestmentCreate
from app.models import Investment, CryptoWallet
from pydantic import BaseModel

router = APIRouter(
    prefix="/crypto",
    tags=["crypto"]
)

class ConnectCryptoRequest(BaseModel):
    platform_id: str # The name of the platform (since we use strings for platform names currently)
    name: str # Wallet Nickname
    xpub: str
    user_id: int

@router.post("/connect-investment")
async def connect_crypto_investment(
    request: ConnectCryptoRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Creates a new Investment entry and links a CryptoWallet to it.
    Triggers an immediate background sync.
    """
    holdings_service = HoldingsService(db, request.user_id)
    crypto_service = CryptoService(db)
    
    # 1. Validate XPUB
    if not crypto_service.validate_xpub(request.xpub):
         raise HTTPException(status_code=400, detail="Invalid XPUB format")

    # 2. Create Investment (placeholder values initially)
    # We set holdings to 0 initially, will update after sync
    inv_create = InvestmentCreate(
        platform=request.platform_id,
        name=request.name,
        symbol="BTC", # Default to BTC for now
        holdings=0.0,
        amount_spent=0.0,
        average_buy_price=0.0,
        current_price=0.0 # Will be updated by price fetcher later
    )
    
    investment = holdings_service.add_investment(request.platform_id, inv_create)
    
    # 3. Create CryptoWallet
    try:
        wallet = crypto_service.create_wallet_for_investment(investment.id, request.xpub)
    except ValueError as e:
        # Rollback investment creation if wallet fails? 
        # For now, just raise
        raise HTTPException(status_code=400, detail=str(e))
        
    # 4. Trigger Sync (Blocking for immediate UX feedback)
    # background_tasks.add_task(crypto_service.sync_wallet, wallet)
    await crypto_service.sync_wallet(wallet)
    
    # Refresh wallet to get updated balance for logging/return if needed
    db.refresh(wallet)
    
    return {
        "status": "success", 
        "investment_id": investment.id, 
        "wallet_id": wallet.id,
        "message": "Wallet connected. Syncing in background."
    }

@router.post("/{wallet_id}/sync")
async def sync_wallet_endpoint(
    wallet_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    crypto_service = CryptoService(db)
    wallet = db.query(CryptoWallet).filter(CryptoWallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
        
    background_tasks.add_task(crypto_service.sync_wallet, wallet)
    return {"status": "sync_started"}
