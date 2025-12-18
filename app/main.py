from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base

# Create tables on startup (for now, until Alembic is set up)
if settings.ENVIRONMENT != "testing":
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Finance API",
    description="Backend API for Personal Finance Tracker",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://finance-web-7xy2.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True, # Keeping True as per previous config and to allow potential auth headers
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """
    Health check endpoint that does not touch the DB.
    Useful for scale-to-zero platforms like Render.
    """
    return {"status": "healthy"}

# Import and include routers
from app.routers import net_worth, holdings, goals, cashflow, analytics

app.include_router(net_worth.router)
app.include_router(holdings.router)
app.include_router(goals.router)
app.include_router(cashflow.router)
app.include_router(analytics.router)

import asyncio
from datetime import datetime
from app.database import SessionLocal
from app.services.analytics_service import AnalyticsService
import logging

logger = logging.getLogger(__name__)

async def run_scheduler():
    """Background task to take net worth snapshots every 15 minutes, aligned to the clock"""
    
    # Wait for the first aligned interval before taking any snapshot
    # This ensures no "random" timestamps (e.g. 00:13) appear in the graph
    logger.info("Scheduler: Started. Waiting for next quarter-hour alignment...")

    while True:
        try:
            # Calculate time to next quarter hour (00, 15, 30, 45)
            now = datetime.utcnow()
            minutes_to_next = 15 - (now.minute % 15)
            seconds_to_wait = (minutes_to_next * 60) - now.second
            
            # Ensure we don't sleep <= 0 (sanity check)
            if seconds_to_wait <= 0:
                 seconds_to_wait = 900
            
            logger.info(f"Scheduler: Waiting {seconds_to_wait}s until next quarter-hour alignment...")
            await asyncio.sleep(seconds_to_wait)

            logger.info("Scheduler: Taking aligned net worth snapshot...")
            db = SessionLocal()
            try:
                # 1. Update all prices first so the snapshot is accurate
                from app.services.holdings_service import HoldingsService
                holdings_service = HoldingsService(db, user_id=1)
                logger.info("Scheduler: Refreshing prices...")
                await holdings_service.update_all_prices_async()
                
                # Auto-sync Trading212 if credentials exist
                try:
                    creds = holdings_service.get_trading212_credentials()
                    if creds:
                        logger.info("Scheduler: Auto-syncing Trading212...")
                        await holdings_service.sync_trading212_investments(creds['api_key_id'], creds['api_secret_key'])
                except Exception as e:
                    logger.error(f"Scheduler: Auto-sync failed: {e}")
                
                # 2. Capture the snapshot with fresh prices
                service = AnalyticsService(db, user_id=1)
                service.capture_snapshot()
                service.cleanup_history()
                logger.info("Scheduler: Snapshot completed successfully")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(60) # Backoff on error

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_scheduler())
