from fastapi import HTTPException

from app.config import settings


def is_local_or_demo_runtime() -> bool:
    environment = settings.ENVIRONMENT.strip().casefold()
    return (
        environment in {"local", "demo", "test", "testing"}
        or settings.DATABASE_URL.startswith("sqlite")
    )


def require_remote_data_enabled() -> None:
    """Block network-backed data actions in local/demo unless explicitly opted in."""
    if is_local_or_demo_runtime() and not settings.ENABLE_REMOTE_DATA:
        raise HTTPException(
            status_code=403,
            detail="Remote data access is disabled for this local/demo runtime",
        )
