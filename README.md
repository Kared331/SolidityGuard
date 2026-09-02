<div align="center">

# SolidGuard

**企业级 Solidity 智能合约审计平台**
**Enterprise-Grade Solidity Smart Contract Audit Platform**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 项目简介

SolidGuard 是一个集**静态分析**、**模糊测试**与 **LLM 深度审计**于一体的智能合约自动化审计平台，通过 RAG 检索增强生成技术注入 SWC Registry 漏洞知识库，显著提升漏洞检出率与误报控制能力。

### 核心亮点

| 维度 | 亮点 |
|------|------|
| **三阶段审计流水线** | Slither 静态分析 → Foundry 模糊测试 → LLM 深度审计（RAG 增强） |
| **性能优化成果** | 审计总延迟从 **210s 降至 70s**（降幅 67%），非 LLM 开销从 40s 降至 1.7s |
| **并发架构** | 文件级并行（5 workers）+ 函数级并行（单文件 N>5 时启用，实测 3.79x 加速）+ 批量化 Embedding/DB 写入 |
| **模块解耦** | TaskDispatcher Protocol 消除 Service/Task 循环依赖，支持独立单元测试 |
| **配置热加载** | 基于 mtime 的配置缓存，LLM Provider/Token Budget 修改即时生效，无需重启 |
| **一键管理门户** | `manage.ps1` 交互式脚本，封装启停、日志、配置修改、健康检查全流程 |

### 快速启动

```powershell
# Windows 一键启动（推荐）
cd D:\SolidGuard
.\manage.ps1                 # 交互菜单
.\manage.ps1 -Up             # 直接启动服务
# 首次运行自动进入配置引导：回车即随机生成数据库/Redis 密码与 API Key，无需手动改 .env
```

```bash
# 跨平台 Docker 启动
docker compose up -d
```

启动后访问：前端 [http://localhost:3000](http://localhost:3000) ｜ API [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Features

| Feature | Description |
|---------|-------------|
| **Static Analysis** | Detect reentrancy, overflow, access control, and 40+ Solidity vulnerability patterns via [Slither](https://github.com/crytic/slither) |
| **Fuzz Testing** | Property-based fuzzing with automatic test generation via [Foundry](https://github.com/foundry-rs/foundry) |
| **LLM Deep Audit** | AI-powered code review with configurable token budgets, RAG-enhanced context, and multi-provider routing |
| **RAG Enhancement** | Retrieve similar known vulnerabilities from SWC Registry via ChromaDB to augment LLM context |
| **Multi-Provider LLM** | Unified client supporting OpenAI-compatible APIs and Anthropic Messages API |
| **False Positive Feedback** | Mark detections as false positive; auto-excluded from subsequent reports |
| **Multi-format Reports** | Professional audit reports with severity coding (Critical/High/Medium/Low/Info) in HTML / PDF / Word |
| **Real-time Progress** | SSE-based live task progress streaming |
| **Hot Configuration** | LLM provider/model/token budget changes take effect on next task — no restart required |

---

## Performance Highlights

Engineering optimizations applied to the audit pipeline:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Total audit latency** | 210s | 70s | **67% reduction** |
| **Non-LLM overhead** | 40s | 1.7s | **95% reduction** |
| **Embedding I/O** | Sequential per-file | Batched (32/request) | 20x throughput |
| **Database writes** | N+1 session commits | Single-session batch commit | Atomic & fast |
| **LLM calls (cross-file)** | Sequential per-file | File-level parallelism (5 workers) | 5.22x concurrency |
| **LLM calls (within-file)** | Sequential per-function | Function-level parallelism (N>5) | 3.79x speedup |
| **Test coverage** | — | 95 unit + 20 integration + 7 perf benchmarks | All green |

**Key techniques:** `ThreadPoolExecutor(max_workers=5)` + `Semaphore(5)` for file-level parallelism · **function-level parallelism** (threshold N>5, aligned with LLM Semaphore) for within-file multi-function contracts · batch embedding (limit 32) · single-session batch commit for findings · `TaskDispatcher` Protocol for Service/Task decoupling.

---

## Quick Start

### Option A: One-Click Management Script (Windows)

```powershell
cd D:\SolidGuard
.\manage.ps1              # Interactive menu (recommended)
.\manage.ps1 -Up          # Start services directly
.\manage.ps1 -Config      # Enter config management
.\manage.ps1 -Health      # Health check
```

The script handles Docker detection, config bootstrap, container build/start, PostgreSQL health wait, and access info display. On first run (or when `changeme` defaults remain), an interactive wizard guides credential setup — press Enter to auto-generate random passwords/API keys, so the first startup is a single closed-loop command with no manual `.env` editing.

### Option B: Docker Compose (Cross-Platform)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) + LLM API key (OpenAI / Anthropic / compatible)

```bash
# 1. Configure
cp .env.example .env              # Edit passwords and API keys
cp solidguard.json.example solidguard.json

# 2. Launch (auto-runs database migrations)
docker compose up -d
```

### Access Endpoints

| Service | URL |
|---------|-----|
| Frontend | [http://localhost:3000](http://localhost:3000) |
| API | [http://localhost:8000](http://localhost:8000) |
| Swagger Docs | [http://localhost:8000/docs](http://localhost:8000/docs) |
| Health Check | [http://localhost:8000/health](http://localhost:8000/health) |

---

## Architecture

### System Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Frontend (SPA) │     │   API (FastAPI)  │     │ Worker (Celery)  │
│   React + Vite  │     │   :8000          │     │                  │
│   :3000         │     │                  │     │  ┌────────────┐  │
│                 │     │  ┌────────────┐  │     │  │  Slither   │  │
│  nginx proxy ───┼─────┼─►│  Routes    │  │     │  │  Foundry   │  │
│  (injects key)  │     │  │  /api/v1/* │  │     │  │  LLM Audit │  │
│                 │     │  └─────┬──────┘  │     │  └─────┬──────┘  │
└─────────────────┘     │        │         │     └────────┼─────────┘
                        │  ┌─────▼──────┐  │              │
                        │  │  Services   │◄─┼──────────────┘
                        │  │  (Protocol) │  │  TaskDispatcher
                        │  └─────┬──────┘  │  decoupling
                        └────────┼─────────┘
                                 │
            ┌────────────┬───────┴────────┐
            │            │                │
     ┌──────▼──────┐ ┌───▼────┐  ┌───────▼───────┐
     │ PostgreSQL  │ │ Redis  │  │   ChromaDB    │
     │   :5432     │ │ :6379  │  │  (RAG vector)  │
     └─────────────┘ └────────┘  └───────┬───────┘
                                          │
                                 ┌────────▼────────┐
                                 │    LLM API      │
                                 │ (OpenAI/Anthr…) │
                                 └─────────────────┘
```

### Key Design Decisions

- **TaskDispatcher Protocol** — Eliminates circular dependency between Service and Task layers; enables independent unit testing of business logic without Celery.
- **Three-Stage Audit Pipeline** — Collection → Batch prefetch → Audit. Each stage independently optimized for I/O and concurrency.
- **File-Level Parallelism** — `ThreadPoolExecutor(max_workers=5)` with aligned `Semaphore(5)` for concurrent LLM calls across contract files.
- **Function-Level Parallelism (P4)** — When a single contract exposes >5 key functions, a second `ThreadPoolExecutor(5)` parallelizes per-function LLM audits within the file. Threshold aligned with the global LLM Semaphore to avoid thread inflation under nested file+function parallelism. Baseline benchmark: 10-function contract 689.6ms → 181.8ms (3.79x).
- **Single Source of Truth Config** — `.env` for infrastructure secrets, `solidguard.json` for structured app config with `${VAR}` interpolation. No scattered URL definitions.
- **Hot Reload via mtime** — Config changes detected by file mtime caching; LLM provider/model/budget updates take effect on next task without service restart.
- **Async Everywhere** — FastAPI + SQLAlchemy async + HTTPX for non-blocking I/O throughout the stack.

### Docker Compose Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `api` | python:3.11-slim | 8000 | FastAPI app (auto-runs Alembic migrations on start) |
| `worker` | python:3.11-slim | — | Celery worker (Slither, Foundry, LLM audit) |
| `postgres` | postgres:15 | 5432 | Primary database |
| `redis` | redis:7 | 6379 | Celery broker, cache, rate limiter |
| `frontend` | nginx:alpine | 3000 | React SPA + reverse proxy |
| `nginx-proxy` | nginx:alpine | 80/443 | Optional HTTPS termination (profile: `https`) |

---

## Audit Pipeline

```
1. Upload Contracts          POST /api/v1/projects
       │
2. Slither Static Analysis   POST /projects/{id}/analyze
       │
3. Foundry Fuzz Testing      POST /projects/{id}/fuzz
       │
4. LLM Deep Audit            POST /projects/{id}/llm-audit
       │     │  RAG: ChromaDB ──── SWC knowledge base
       │     │  Parallel: ThreadPoolExecutor (5 workers)
       │
5. Generate Report           POST /projects/{id}/report
       │
6. Download                  GET  /reports/{id}/download
```

### RAG Strategy

| Step | Action | Purpose |
|------|--------|---------|
| **1. Summarize** | Compress contract to interface + state variables + function signatures | Reduce context window usage |
| **2. Extract** | Identify functions with external calls (`transfer`, `call`, `delegatecall`) | Focus on high-risk code paths |
| **3. Retrieve** | Embed function code, query ChromaDB for top-K similar vulnerabilities | Inject known attack patterns |
| **4. Audit** | LLM receives summary + function body + similar vulnerabilities as context | Enhanced pattern recognition |

---

## Configuration

SolidGuard uses a **JSON config file** (`solidguard.json`) for application settings, with `.env` only for infrastructure secrets and `${VAR}` interpolation.

### Key Settings

| Field | Default | Description |
|-------|---------|-------------|
| `app.apiKey` | — | API access key (supports `${API_KEY}`) |
| `app.tokenBudget` | `500000` | Max tokens per project for LLM audit |
| `app.maxLLMCallsPerProject` | `100` | Max LLM API calls per project |
| `app.rateLimit` | `"120/minute"` | Per-IP rate limit |
| `database.poolSize` | `10` | Connection pool size |
| `rag.topK` | `5` | Similar vulnerabilities to retrieve |
| `providers.*.api` | — | `"openai"` / `"anthropic-messages"` / `"local"` |

> Embedding provider supports `"local"` mode using `sentence-transformers` (all-MiniLM-L6-v2) — no API key required.

### Environment Variables (`.env`)

| Variable | Required | Description |
|----------|:--------:|-------------|
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `REDIS_PASSWORD` | Yes | Redis password |
| `API_KEY` | Yes | API access key |
| `LLM_API_KEY` | Yes | LLM provider API key |
| `XIAOMI_API_KEY` | No | Xiaomi Mimo provider key |
| `GITHUB_TOKEN` | No | For SWC sync rate limiting |

---

## API Reference

| Category | Key Endpoints |
|----------|---------------|
| **Projects** | `POST /api/v1/projects` (upload) · `GET /api/v1/projects/{id}` |
| **Analysis** | `POST /api/v1/projects/{id}/analyze` (Slither) · `/fuzz` (Foundry) · `/llm-audit` (LLM) |
| **Reports** | `POST /api/v1/projects/{id}/report` · `GET /api/v1/reports/{id}/download` |
| **Knowledge** | `POST /api/v1/knowledge/sync` (SWC Registry) · `GET /api/v1/vulnerabilities` |
| **Real-time** | `GET /api/v1/projects/{id}/events` (SSE stream) |
| **Health** | `GET /health` |

> Full interactive docs: **http://localhost:8000/docs** (Swagger UI)

---

## Project Structure

```
SolidGuard/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI routes (v1/, projects, analysis, llm_audit, reports)
│   │   ├── llm/                    # LLM module
│   │   │   ├── budget/             # Token budget management (thread-safe)
│   │   │   ├── pipeline/           # Three-stage audit pipeline
│   │   │   ├── provider/           # Multi-provider routing
│   │   │   ├── rag/                # RAG retrieval logic
│   │   │   ├── prompts/            # Prompt templates
│   │   │   └── config.py           # Config parser + hot reload
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── services/               # Business logic (engine/, infra/, templates/)
│   │   ├── tasks/                  # Celery tasks (TaskDispatcher Protocol)
│   │   ├── state/                  # Project state machine
│   │   ├── config.py               # Settings from JSON config
│   │   └── main.py                 # FastAPI entry
│   └── alembic/                    # Database migrations
├── frontend/
│   ├── src/                        # React + TypeScript (pages, design-system, hooks, stores)
│   └── nginx.conf                  # Reverse proxy + SPA fallback
├── tests/                          # 95 unit + 20 integration + 7 perf benchmarks
├── manage.ps1                      # Windows management portal
├── docker-compose.yml              # Service orchestration
├── solidguard.json                 # Application configuration
└── .env.example                    # Environment template
```

---

## Development

### Local Setup (without Docker)

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000      # API
celery -A app.celery_app worker -B --loglevel=info  # Worker

# Frontend
cd frontend && npm install && npm run dev       # → http://localhost:5173
```

### Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "description"   # Generate
alembic upgrade head                                # Apply
alembic downgrade -1                                # Rollback
```

### Testing

```bash
# 单元测试（无需 Docker 服务栈，默认排除集成测试与性能压测）
venv\Scripts\python.exe -m pytest tests -m "not integration and not perf" -v

# 集成测试（需 docker compose up -d 运行中，全部走 127.0.0.1）
venv\Scripts\python.exe -m pytest tests -m integration -v

# 性能压测（显式运行，不计入 CI 必跑）
venv\Scripts\python.exe -m pytest tests/perf -m perf -v -s
```

> **测试声明（E8）**：95 项单测（`pytest -m "not integration and not perf"`）全绿；20 项集成测试（`pytest -m integration`）需 Docker 服务栈运行时可执行，服务不可达时自动 SKIP；7 项性能压测（`pytest -m perf`）需显式运行，含 P4-3 函数级并行优化守护（场景 F/G）。以上数字经 `2026-09-01` 实测验证。

### HTTPS Deployment

```bash
docker compose --profile https up -d               # Enable nginx TLS proxy
```

---

## TROUBLESHOOTING

试运行期间实测踩坑记录（现象 → 根因 → 解法），与 `manage.ps1 doctor` 自检命令（P2-6）互相引用。

### 1. API 容器启动即崩溃且永不自愈

- **现象**：`docker compose up` 后 api 容器 2 秒退出，日志报数据库连接失败。
- **根因**：`.env` 中写死了 `DATABASE_URL=...@localhost`，其优先级高于 compose 的 `POSTGRES_HOST=postgres` 覆盖；且旧版 compose 无 restart policy。
- **解法**：注释 `.env` 中 `DATABASE_URL`/`REDIS_URL` 完整连接串（保留组件变量 `POSTGRES_*`/`REDIS_*`）；compose 已加 `restart: unless-stopped`（P1-5）。详见 `.env.example` 顶部注释。

### 2. Alembic 迁移报 `NoSuchModuleError: driver`

- **现象**：容器启动执行 `alembic upgrade head` 时报 `NoSuchModuleError: driver`。
- **根因**：`alembic/env.py` 只认 `DATABASE_URL` 环境变量，缺失时落到 `alembic.ini` 模板占位符 `driver://`，绕过统一配置构建器。
- **解法**：`env.py` 已增加回退 `settings.DATABASE_URL`（恢复单一事实来源 A3）。

### 3. 前端访问报 `ERR_CONNECTION_RESET` / 页面白屏

- **现象**：浏览器访问 `http://localhost:3000` 连接被重置。
- **根因**：Windows 将 `localhost` 优先解析为 IPv6 `::1`，本机 Docker Desktop 的 IPv6 回环端口转发损坏。
- **解法**：**一律使用 `127.0.0.1`** 代替 `localhost`（V2 约束）。

---

## FAQ

<details>
<summary><b>Which LLM providers are supported?</b></summary>

Any OpenAI-compatible API (OpenAI, Azure, Xiaomi Mimo, local models) and Anthropic Messages API. Set `"api": "openai"` or `"api": "anthropic-messages"` in `solidguard.json`. Multiple providers can coexist.

</details>

<details>
<summary><b>How does configuration hot-reload work?</b></summary>

The config module caches file mtime. On each config access, if mtime changed, the JSON is re-parsed. This means LLM provider/model/token budget edits in `solidguard.json` take effect on the next task — no service restart needed.

</details>

<details>
<summary><b>How does RAG improve the LLM audit?</b></summary>

Before auditing each function, the system embeds the function code and queries ChromaDB for top-K similar known vulnerabilities from the SWC Registry. These are injected into the LLM prompt as context, enabling pattern recognition the model might otherwise miss.

</details>

<details>
<summary><b>How are false positives handled?</b></summary>

Users mark individual detections as false positive via the UI. Marked items persist in the database and are automatically excluded from all subsequent analysis views and report generation.

</details>

---

## Contributing

1. Fork → `git checkout -b feature/amazing-feature`
2. Commit → `git commit -m 'Add amazing feature'`
3. Push → `git push origin feature/amazing-feature`
4. Open a Pull Request (ensure all tests pass)

---

## License

MIT License — see [LICENSE](LICENSE).

---

<div align="center">

**Built with** Python · FastAPI · Celery · PostgreSQL · Redis · ChromaDB · React · TypeScript · Slither · Foundry · Docker

</div>
