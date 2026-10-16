import asyncio
import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text
from starlette.responses import JSONResponse

from app.api.router import api_router
from app.config import settings
from app.database import async_engine, async_session

logger = logging.getLogger("solidguard")

def _rate_limit_key(request: Request) -> str:
    """限流键：优先取 X-Forwarded-For 末段（受信代理 append 的真实来源）。

    经 nginx 代理时 request.client 是容器内代理 IP，直接用会让所有
    用户共享同一限流桶；XFF 末段由 nginx 追加（proxy_add_x_forwarded_for），
    客户端伪造的 XFF 段会被压到前段，不影响末段可信度。
    直连 API（无代理头）时回退到 remote address。

    已知取舍：https profile（nginx-proxy → frontend 双跳）下末段为内层
    代理 IP，退化为全局共享桶——保守方向（只会更严），可接受。
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return get_remote_address(request)


# Rate limiting (Fix #11) + A1 激活
limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=[settings.RATE_LIMIT],
    storage_uri=settings.REDIS_URL,
    # A1: Redis 不可用时降级为进程内限流（同额度），避免存储故障放大为 500
    in_memory_fallback=[settings.RATE_LIMIT],
)


# P2-4: lifespan 迁移——消除 @app.on_event("shutdown") 弃用警告；
# P1-4 的 Provider/loop 关闭逻辑迁入此处，避免二次改 main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup（当前无 startup 钩子逻辑，limiter 在模块级已初始化）
    yield
    # shutdown
    logger.info("Shutting down: closing database connections...")
    await async_engine.dispose()

    # P1-4: 关闭 Provider HTTP 客户端（与 worker_process_shutdown 钩子对称，S7 生命周期统一）
    try:
        from app.llm.provider.provider_registry import get_provider_registry

        registry = get_provider_registry()
        provider = registry.get()
        if hasattr(provider, "close"):
            await provider.close()
            logger.info("Provider HTTP 客户端已关闭")
    except Exception as exc:
        logger.debug("关闭 Provider 时跳过: %s", exc)

    # 关闭 sync_wrapper 常驻事件循环（若已初始化）
    try:
        from app.llm import sync_wrapper

        if sync_wrapper._loop is not None and not sync_wrapper._loop.is_closed():
            sync_wrapper._loop.call_soon_threadsafe(sync_wrapper._loop.stop)
            logger.info("LLM 常驻事件循环已请求停止")
    except Exception as exc:
        logger.debug("关闭事件循环时跳过: %s", exc)

    logger.info("Shutdown complete.")


app = FastAPI(title="SolidiGuard API", lifespan=lifespan)
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
            body_preview = {
                k: f"<{type(v).__name__} name={getattr(v, 'filename', '?')} size={getattr(v, 'size', '?')}>"
                for k, v in form.items()
            }
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
            "errors": [{"field": " -> ".join(str(loc) for loc in e["loc"]), "message": e["msg"]} for e in errors],
        },
    )


# A1: 激活限流——SlowAPIMiddleware 使 default_limits 对全部路由生效。
# 历史缺陷：仅创建 Limiter 未接中间件/装饰器，RATE_LIMIT 从未实际执行。
# 注册顺序在 CORS 之前（后注册者为最外层），preflight OPTIONS 由 CORS
# 直接短路，不消耗限流配额。
app.add_middleware(SlowAPIMiddleware)

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


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting SolidiGuard API on port %s", settings.APP_PORT)
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.APP_PORT, reload=True)
