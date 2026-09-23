import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    API_TOKEN: str = os.getenv("PERSONAL_API_TOKEN", "dev-token-123")  # Default to dev token if missing to prevent 500s
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() in {"1", "true", "yes", "on"}
    ENABLE_REMOTE_DATA: bool = os.getenv("ENABLE_REMOTE_DATA", "false").lower() in {"1", "true", "yes", "on"}

    class Config:
        env_file = ".env"

settings = Settings()
