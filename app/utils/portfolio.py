from typing import Optional


def is_standalone_cash_platform(platform: Optional[str]) -> bool:
    """Return true only for the standalone platform named Cash."""
    return bool(platform and platform.strip().casefold() == "cash")
