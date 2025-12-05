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
    allow_origins=["*"],  # Allow all origins for now
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
from app.routers import net_worth, holdings, goals, cashflow, analytics

app.include_router(net_worth.router)
app.include_router(holdings.router)
app.include_router(goals.router)
app.include_router(cashflow.router)
app.include_router(analytics.router)
