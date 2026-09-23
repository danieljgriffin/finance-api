from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Use NullPool for Neon scale-to-zero compatibility if needed, 
# or a small pool size if using pgbouncer transaction mode.
# The user specified: "Short-lived SQLAlchemy sessions (NullPool or tiny pool)"
from sqlalchemy.pool import NullPool

SQLALCHEMY_DATABASE_URI = settings.DATABASE_URL
if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

engine_options = {"poolclass": NullPool}
if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URI, **engine_options)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
