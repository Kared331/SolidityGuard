"""Simple API Key authentication dependency (1.3).

Uses a single configurable API key via the ``X-API-Key`` header.
When ``API_KEY`` is not set, a warning is logged and all requests are rejected.

A3 加固：
- 恒定时间比较（hmac.compare_digest，bytes 化以容忍非 ASCII 输入，
  避免恶意 header 触发 TypeError 500）；
- 认证失败审计日志（路径 + 来源 + 是否携带 key，不记录 key 本身），
  使暴力探测在日志中可观测。
"""

import hmac

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from app.config import logger, settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    request: Request, api_key: str | None = Security(_api_key_header)
) -> None:
    """FastAPI dependency – raises 403 when the key is missing, wrong, or not configured."""
    if not settings.API_KEY:
        logger.error("API_KEY is not configured – rejecting all requests")
        raise HTTPException(status_code=403, detail="API key not configured on server")
    if api_key is None or not hmac.compare_digest(
        api_key.encode("utf-8"), settings.API_KEY.encode("utf-8")
    ):
        # A3: 认证失败审计——只记元数据，绝不记录 key 本身
        logger.warning(
            "认证失败: path=%s, client=%s, has_key=%s",
            request.url.path,
            request.client.host if request.client else "unknown",
            api_key is not None,
        )
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
