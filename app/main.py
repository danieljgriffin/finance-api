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

# Authentication Middleware
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

EXEMPT_PATHS = {"/health", "/docs", "/openapi.json"}

@app.middleware("http")
async def bearer_token_auth(request: Request, call_next):
    if request.url.path in EXEMPT_PATHS:
        return await call_next(request)
    
    # Allow CORS preflight requests (OPTIONS) to pass without auth
    if request.method == "OPTIONS":
        return await call_next(request)

    TOKEN = settings.API_TOKEN
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {TOKEN}":
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    return await call_next(request)

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
    allow_credentials=True, 
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
from app.routers import net_worth, holdings, goals, cashflow, analytics, crypto

app.include_router(net_worth.router)
app.include_router(holdings.router)
app.include_router(goals.router)
app.include_router(cashflow.router)
app.include_router(analytics.router)
app.include_router(crypto.router)

import asyncio
from datetime import datetime
from app.database import SessionLocal
from app.services.analytics_service import AnalyticsService
import logging
import sys

# Configure Logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global status for health check
scheduler_status = {
    "last_run": None,
    "last_status": "initializing", 
    "last_error": None,
    "interval_minutes": 5
}

async def run_scheduler():
    """Background task to take net worth snapshots every 5 minutes, aligned to the clock"""
    
    logger.info("Scheduler: Started. Waiting for next 5-minute alignment...")
    
    # Track previous update to prevent double firing if clock skews
    last_processed_minute = -1

    while True:
        try:
            # Calculate time to next 5 minute interval (00, 05, 10, 15 ...)
            now = datetime.utcnow()
            minutes_to_next = 5 - (now.minute % 5)
            seconds_to_wait = (minutes_to_next * 60) - now.second
            
            # Ensure we don't sleep <= 0 (sanity check)
            if seconds_to_wait <= 0:
                 seconds_to_wait = 300
            
            logger.info(f"Scheduler: Waiting {seconds_to_wait}s until next 5-minute alignment...")
            scheduler_status["last_status"] = "waiting"
            await asyncio.sleep(seconds_to_wait)

            logger.info("Scheduler: Taking aligned net worth snapshot...")
            scheduler_status["last_status"] = "running"
            
            db = SessionLocal()
            try:
                # 1. Update all prices first so the snapshot is accurate
                from app.services.holdings_service import HoldingsService
                holdings_service = HoldingsService(db, user_id=1)
                
                logger.info("Scheduler: Refreshing prices...")
                # Add timeout to prevent hanging (Increased to 300s)
                await asyncio.wait_for(holdings_service.update_all_prices_async(), timeout=300)
                
                # Auto-sync Trading212 if credentials exist
                try:
                    creds = holdings_service.get_trading212_credentials()
                    if creds:
                        logger.info("Scheduler: Auto-syncing Trading212...")
                        # Add timeout to prevent hanging (Increased to 300s)
                        await asyncio.wait_for(
                            holdings_service.sync_trading212_investments(creds['api_key_id'], creds['api_secret_key']),
                            timeout=300
                        )
                        logger.info("Scheduler: Trading212 sync completed successfully")
                    else:
                        logger.debug("Scheduler: Skipped T212 sync (no credentials configured)")
                except asyncio.TimeoutError:
                    logger.error("Scheduler: Trading212 sync timed out")
                except Exception as e:
                    logger.error(f"Scheduler: Auto-sync failed: {e}")
                
                # 2. Capture the snapshot with fresh prices
                service = AnalyticsService(db, user_id=1)
                service.capture_snapshot()
                service.cleanup_history()
                
                logger.info("Scheduler: Snapshot completed successfully")
                scheduler_status["last_run"] = datetime.utcnow().isoformat()
                scheduler_status["last_status"] = "completed"
                scheduler_status["last_error"] = None
                
            except asyncio.TimeoutError:
                 logger.error("Scheduler: Price update timed out")
                 scheduler_status["last_error"] = "Timeout"
            except Exception as e:
                 logger.error(f"Scheduler error inner: {e}")
                 scheduler_status["last_error"] = str(e)
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Scheduler error outer: {e}")
            scheduler_status["last_error"] = str(e)
            await asyncio.sleep(60) # Backoff on error

@app.get("/scheduler/status")
def get_scheduler_status():
    """Check the health and status of the background price update scheduler"""
    return scheduler_status

@app.on_event("startup")
async def startup_event():
    # 1. Seed Default User (ID 1) if missing
    # This ensures local testing works immediately without manual DB setup
    try:
        db = SessionLocal()
        from app.models import User
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            logger.info("Startup: Seeding default user (ID 1)...")
            default_user = User(
                id=1, 
                email="local@test.com", 
                preferences={"platform_colors": {}}
            )
            db.add(default_user)
            db.commit()
            logger.info("Startup: Default user seeded successfully.")
        db.close()
    except Exception as e:
        logger.error(f"Startup: Failed to seed user: {e}")

    # 2. Start Scheduler
    asyncio.create_task(run_scheduler())
