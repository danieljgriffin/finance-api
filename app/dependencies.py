from typing import Generator, Optional
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> int:
    """
    Mock authentication dependency.
    In a real app, this would validate a JWT token.
    For now, we accept a user ID in the header or default to 1 for testing.
    """
    if x_user_id:
        try:
            return int(x_user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-User-ID header")
    return 1  # Default to user ID 1 for "get it working for me" phase
