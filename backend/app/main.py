import asyncio
import logging

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from starlette.responses import JSONResponse

from app.api.router import api_router
from app.config import settings
from app.database import async_engine, async_session

logger = logging.getLogger("solidiguard")

# Rate limiting (Fix #11)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT],
    storage_uri=settings.REDIS_URL,
)

app = FastAPI(title="SolidiGuard API")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    body_preview = "unavailable"
    content_type = request.headers.get("content-type", "")

    try:
        if "multipart" in content_type.lower():
            form = await request.form()
            body_preview = {k: f"<{type(v).__name__} name={getattr(v, 'filename', '?')} size={getattr(v, 'size', '?')}>" for k, v in form.items()}
        else:
            body = await request.body()
            body_preview = body.decode("utf-8", errors="replace")[:500]
    except Exception:
        body_preview = "<parse error>"

    logger.warning(
        "422 Validation Error | URL: %s | Content-Type: %s | Body: %s | Errors: %s",
        request.url.path,
        content_type,
        body_preview,
        errors,
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "请求参数校验失败",
            "errors": [
                {"field": " -> ".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
                for e in errors
            ],
        },
    )


# CORS configuration (Fix #9)
_allowed_origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["X-API-Key", "Content-Type"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    checks = {}
    overall = "ok"

    async def _check_postgres():
        async with async_session() as session:
            await session.execute(text("SELECT 1"))

    async def _check_redis():
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()

    # PostgreSQL check
    try:
        await asyncio.wait_for(_check_postgres(), timeout=3)
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"
        overall = "degraded"

    # Redis check
    try:
        await asyncio.wait_for(_check_redis(), timeout=3)
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
        overall = "degraded"

    status_code = 200 if overall == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks},
    )


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down: closing database connections...")
    await async_engine.dispose()
    logger.info("Shutdown complete.")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting SolidiGuard API on port %s", settings.APP_PORT)
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.APP_PORT, reload=True)
