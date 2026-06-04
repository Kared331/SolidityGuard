import os
import sys
import logging

# ─── Logging (4.21) ─────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("solidiguard")

# ─── Database (4.15) ────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    logger.warning(
        "DATABASE_URL not set, using default local PostgreSQL connection"
    )
    DATABASE_URL = "postgresql+asyncpg://solidiguard:solidiguard@localhost:5432/solidiguard"

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
APP_PORT = int(os.environ.get("APP_PORT", "8000"))

# ─── Upload limits (1.24) ───────────────────────────────────────
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50"))
MAX_UPLOAD_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# ─── Cleanup (5.20) ─────────────────────────────────────────────
CLEANUP_DAYS = int(os.environ.get("CLEANUP_DAYS", "30"))

# ─── API Key (1.3) ──────────────────────────────────────────────
API_KEY = os.environ.get("API_KEY", "")
