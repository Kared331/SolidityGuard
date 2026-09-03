"""Simple API Key authentication dependency (1.3).

Uses a single configurable API key via the ``X-API-Key`` header.
When ``API_KEY`` is not set, a warning is logged and all requests are rejected.
"""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import logger, settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency – raises 403 when the key is missing, wrong, or not configured."""
    if not settings.API_KEY:
        logger.error("API_KEY is not configured – rejecting all requests")
        raise HTTPException(status_code=403, detail="API key not configured on server")
    if api_key is None or api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
