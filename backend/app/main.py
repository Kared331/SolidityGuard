import logging

from fastapi import FastAPI
from sqlalchemy import text

from app.api.router import api_router
from app.config import APP_PORT
from app.database import async_session

logger = logging.getLogger("solidiguard")

app = FastAPI(title="SolidiGuard API")
app.include_router(api_router)


@app.get("/health")
async def health():
    async with async_session() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting SolidiGuard API on port %s", APP_PORT)
    uvicorn.run("app.main:app", host="0.0.0.0", port=APP_PORT, reload=True)
