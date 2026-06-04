# SolidiGuard Sprint 0 - Infrastructure Skeleton Design Document

> Source: MetaGPT output (extracted and reviewed)
> Reviewer adjustments applied to ensure Sprint 0 compliance

---

## 1. Implementation Approach

Modern, minimal infrastructure for SolidiGuard using:
- **Python 3.11 + FastAPI** for the API layer (来源: 技术栈约束)
- **PostgreSQL 15** as the primary database with async SQLAlchemy 2.0 + asyncpg (来源: 技术栈约束)
- **Celery + Redis** for background task queue (broker only, no tasks defined) (来源: 技术栈约束 + Sprint 0)
- **Alembic** for database migrations (empty migration only) (来源: Sprint 0)
- **Docker Compose** orchestrating api, postgres, redis services (来源: Sprint 0)

Key design decisions:
1. **Async Architecture**: Full async stack with FastAPI and SQLAlchemy async
2. **Database Layer**: SQLAlchemy 2.0 async with asyncpg driver
3. **Background Tasks**: Celery configured with Redis broker, zero tasks
4. **Database Migrations**: Alembic with async support, empty initial migration
5. **Health Monitoring**: Single `/health` endpoint verifying DB connectivity via SELECT 1
6. **Configuration**: Environment variables via `.env` file
7. **Containerization**: Docker Compose with service dependencies and networking

---

## 2. Directory Structure

```
D:\MetaGPT_Project\SolidGuard\
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── config.py            # Environment variable loading
│   │   ├── database.py          # SQLAlchemy async engine/session
│   │   └── celery_app.py        # Celery instance configuration
│   ├── alembic/
│   │   ├── env.py               # Alembic environment config (async)
│   │   ├── script.py.mako       # Alembic migration template
│   │   └── versions/            # Migration files (empty initial)
│   ├── alembic.ini              # Alembic configuration
│   └── requirements.txt         # Python dependencies
├── docker/
│   └── Dockerfile               # API service Dockerfile
├── docker-compose.yml           # Service orchestration
├── .env.example                 # Environment variable template
└── README.md                    # Basic project readme
```

来源: Sprint 0 任务描述第1-7条

---

## 3. Environment Variables (.env.example)

| Variable | Example Value | Purpose |
|----------|---------------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@postgres:5432/solidiguard` | PostgreSQL async connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `APP_PORT` | `8000` | API server port |

来源: Sprint 0 任务描述第7条

---

## 4. API Design

### GET /health
- **Purpose**: Verify application is running and DB is connected
- **Implementation**: Execute `SELECT 1` via SQLAlchemy async session
- **Response**: `{"status": "ok"}`
- **Error**: Returns 500 if DB connection fails

来源: Sprint 0 任务描述第5条

---

## 5. Database Layer (SQLAlchemy 2.0 Async)

### Components
- `create_async_engine` with DATABASE_URL from environment
- `async_sessionmaker` for session management
- `DeclarativeBase` class (empty, no models)
- Alembic configured for async migrations with `asyncpg` driver

### Migration Strategy
- Single empty initial migration (no tables)
- Alembic env.py configured to use async engine

来源: Sprint 0 任务描述第2条

---

## 6. Celery Configuration

### Components
- Celery app instance with Redis as broker
- Redis as result backend
- **No tasks defined** — only the app configuration object

来源: Sprint 0 任务描述第3条

---

## 7. Docker Compose Services

| Service | Image | Ports | Depends On | Volumes |
|---------|-------|-------|------------|---------|
| `api` | Custom Dockerfile | `8000:8000` | postgres, redis | `./uploads:/app/uploads` |
| `postgres` | `postgres:15` | `5432:5432` | — | `pgdata:/var/lib/postgresql/data` |
| `redis` | `redis:7` | `6379:6379` | — | — |

### Network
- All services on a single bridge network `solidiguard-net`

### Volumes
- `pgdata` — PostgreSQL data persistence
- `./uploads` — File upload directory (host mount)

来源: Sprint 0 任务描述第4条

---

## 8. Dockerfile (API Service)

- Base: `python:3.11-slim`
- Install dependencies from requirements.txt
- Copy backend code
- Run with `uvicorn app.main:app --host 0.0.0.0 --port 8000`

来源: 技术栈约束 (FastAPI + Uvicorn)

---

## 9. Requirements (pinned)

```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
alembic
celery[redis]
redis
python-multipart
```

来源: Sprint 0 任务描述第6条

---

## 10. Component Interaction

```
Client → Docker Compose
  ├── api (FastAPI + Uvicorn)
  │     ├── /health → SQLAlchemy → PostgreSQL (SELECT 1)
  │     └── Celery app → Redis (broker connection only)
  ├── postgres (15)
  └── redis (7)
```

来源: Sprint 0 任务描述

---

## Design Compliance Checklist

| Sprint 0 Requirement | Status |
|----------------------|--------|
| Python 3.11 + FastAPI | ✅ |
| PostgreSQL 15 + SQLAlchemy 2.0 async + asyncpg | ✅ |
| Celery + Redis (no tasks) | ✅ |
| Alembic (empty migration) | ✅ |
| Docker Compose (api, postgres, redis) | ✅ |
| GET /health → {"status": "ok"} + DB check | ✅ |
| Only listed dependencies | ✅ |
| .env.example | ✅ |
| No business logic | ✅ |
| No future-compatible abstractions | ✅ |
