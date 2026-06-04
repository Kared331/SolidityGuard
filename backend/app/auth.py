"""Simple API Key authentication dependency (1.3).

Uses a single configurable API key via the ``X-API-Key`` header.
If ``API_KEY`` is empty or not set the check is skipped (useful for local dev).
"""

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import API_KEY, logger

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency – raises 403 when the key is required but missing/wrong."""
    if not API_KEY:
        # No key configured → open access (dev mode)
        return
    if api_key is None or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
