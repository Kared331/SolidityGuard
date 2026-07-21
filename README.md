<div align="center">

# SolidGuard

**Enterprise-Grade Solidity Smart Contract Audit Platform**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Automated vulnerability detection through **static analysis**, **fuzz testing**, and **LLM-powered deep audit** with RAG enhancement.

[Quick Start](#-quick-start) · [Features](#-features) · [Architecture](#-architecture) · [API Reference](#-api-reference) · [Documentation](#-documentation)

</div>

---

## Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Architecture](#-architecture)
- [Audit Pipeline](#-audit-pipeline)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [Documentation](#-documentation)
- [Development Guide](#-development-guide)
- [Testing](#-testing)
- [FAQ](#-faq)
- [Contributing](#-contributing)
- [License](#-license)

---

## Features

| Feature | Description | Implementation |
|---------|-------------|----------------|
| **Static Analysis** | Detect common Solidity vulnerabilities (reentrancy, overflow, access control, etc.) | [Slither](https://github.com/crytic/slither) |
| **Fuzz Testing** | Property-based testing with automatic test generation and edge-case discovery | [Foundry](https://github.com/foundry-rs/foundry) |
| **LLM Deep Audit** | AI-powered code review with configurable token budgets and call limits | OpenAI / Anthropic / Mimo |
| **RAG Enhancement** | Retrieve similar known vulnerabilities from SWC Registry to augment LLM context | ChromaDB + SWC Registry |
| **Multi-Provider LLM** | Support OpenAI-compatible APIs and Anthropic Messages API with provider routing | HTTPX async client |
| **False Positive Feedback** | Mark detections as false positive; auto-excluded from subsequent reports | Built-in |
| **Vulnerability Knowledge Base** | SWC Registry sync with vector search and semantic matching | ChromaDB |
| **Multi-format Reports** | Professional audit reports with severity coding (Critical/High/Medium/Low/Info) | HTML / PDF / Word |
| **Real-time Progress** | SSE-based live task progress and result notifications | EventSource |
| **Rate Limiting** | Configurable per-IP rate limiting via Redis backend | SlowAPI |
| **Input Sanitization** | LLM prompt injection defense and malicious input filtering | Custom sanitizer |

---

## Tech Stack

### Backend

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (async) |
| **Task Queue** | Celery + Redis broker |
| **ORM** | SQLAlchemy (async) + Alembic migrations |
| **Database** | PostgreSQL 15 |
| **Cache / Broker** | Redis 7 |
| **Vector Store** | ChromaDB (local persistence) |
| **HTTP Client** | HTTPX (async) |
| **Report Generation** | Jinja2 + WeasyPrint (PDF) + python-docx (Word) |

### Frontend

| Component | Technology |
|-----------|------------|
| **Framework** | React 18 + TypeScript |
| **Build Tool** | Vite 5 |
| **State Management** | Zustand |
| **Data Fetching** | TanStack React Query + Axios |
| **Routing** | React Router v6 |

### Analysis Tools

| Tool | Purpose |
|------|---------|
| **Slither** | Static analysis for Solidity |
| **Foundry** | Fuzz testing framework |
| **solc-select** | Solidity compiler version management |

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/) installed
- LLM API key (OpenAI, Anthropic, or any OpenAI-compatible provider)

### 1. Clone and Configure

```bash
git clone git@github.com:Kared331/SolidityGuard.git
cd SolidityGuard

# Copy environment template
cp .env.example .env
cp solidguard.json.example solidguard.json
```

### 2. Set Environment Variables

Edit `.env`:

```env
# Database
POSTGRES_USER=solidguard
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=solidguard

# Redis
REDIS_PASSWORD=your-secure-password

# API
API_KEY=your-random-api-key

# LLM
LLM_API_KEY=your-llm-api-key

# (Optional) Xiaomi Mimo provider
XIAOMI_API_KEY=your-xiaomi-api-key

# (Optional) GitHub token for SWC sync rate limiting
GITHUB_TOKEN=
```

### 3. Configure LLM Provider

Edit `solidguard.json` — see [Configuration](#-configuration) for full details.

**OpenAI / Compatible:**

```json
{
  "providers": {
    "default": {
      "apiKey": "${LLM_API_KEY}",
      "baseUrl": "https://api.openai.com/v1",
      "api": "openai",
      "defaultModel": "gpt-4o",
      "models": [
        {
          "id": "gpt-4o",
          "name": "GPT-4o",
          "maxTokens": 4096,
          "contextWindow": 128000
        }
      ]
    }
  }
}
```

**Anthropic:**

```json
{
  "providers": {
    "default": {
      "apiKey": "${LLM_API_KEY}",
      "baseUrl": "https://api.anthropic.com",
      "api": "anthropic-messages",
      "defaultModel": "claude-sonnet-4-20250514",
      "models": [
        {
          "id": "claude-sonnet-4-20250514",
          "name": "Claude Sonnet 4",
          "maxTokens": 4096,
          "contextWindow": 200000
        }
      ]
    }
  }
}
```

### 4. Launch

```bash
docker compose up -d
```

### 5. Access

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | [http://localhost:3000](http://localhost:3000) | Web UI |
| **API** | [http://localhost:8000](http://localhost:8000) | REST API |
| **API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI |
| **Health** | [http://localhost:8000/health](http://localhost:8000/health) | Service health check |

---

## Configuration

SolidGuard uses a **JSON configuration file** (`solidguard.json`) for application settings. Environment variables are only used for Docker infrastructure and sensitive values referenced via `${VAR}` syntax.

### Application Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `app.apiKey` | string | — | API access key (supports `${API_KEY}`) |
| `app.port` | number | `8000` | API server port |
| `app.maxUploadSizeMb` | number | `50` | Max upload file size in MB |
| `app.cleanupDays` | number | `30` | Days before auto-cleanup of old projects |
| `app.logLevel` | string | `"INFO"` | Logging level |
| `app.corsOrigins` | string | — | Comma-separated allowed CORS origins |
| `app.rateLimit` | string | `"60/minute"` | Rate limit expression |
| `app.tokenBudget` | number | `500000` | Max tokens per project for LLM audit |
| `app.maxLLMCallsPerProject` | number | `100` | Max LLM API calls per project |

### Database & Cache

| Field | Type | Description |
|-------|------|-------------|
| `database.url` | string | PostgreSQL connection string (supports `${VAR}`) |
| `database.poolSize` | number | Connection pool size |
| `database.maxOverflow` | number | Max overflow connections |
| `redis.url` | string | Redis connection string (supports `${VAR}`) |

### RAG Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `rag.chromaPersistDir` | string | `"./chroma_data"` | ChromaDB persistence directory |
| `rag.topK` | number | `5` | Number of similar vulnerabilities to retrieve |

### LLM Provider Configuration

Each provider object supports:

| Field | Type | Description |
|-------|------|-------------|
| `apiKey` | string | API key (supports `${ENV_VAR}`) |
| `baseUrl` | string | API base URL |
| `api` | string | `"openai"`, `"anthropic-messages"`, or `"local"` |
| `defaultModel` | string | Default model ID |
| `models` | array | Available models with `id`, `name`, `maxTokens`, `contextWindow` |

The `embedding` provider supports `"local"` mode using `sentence-transformers` with `all-MiniLM-L6-v2` — no API key required.

### Environment Variables (`.env`)

| Variable | Required | Description |
|----------|:--------:|-------------|
| `POSTGRES_USER` | Yes | PostgreSQL user |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_DB` | Yes | Database name |
| `REDIS_PASSWORD` | Yes | Redis password |
| `API_KEY` | Yes | API access key |
| `LLM_API_KEY` | Yes | LLM provider API key |
| `XIAOMI_API_KEY` | No | Xiaomi Mimo provider key |
| `GITHUB_TOKEN` | No | GitHub token for SWC sync rate limiting |
| `SOLIDGUARD_CONFIG` | No | Config file path (default: `./solidguard.json`) |
| `VITE_API_BASE_URL` | No | Frontend API base path (default: `/api`) |

---

## Architecture

### System Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Frontend (SPA) │     │   API (FastAPI)  │     │ Worker (Celery)  │
│   React + Vite  │     │   :8000          │     │                  │
│   :3000         │     │                  │     │                  │
│                 │     │  ┌────────────┐  │     │  ┌────────────┐  │
│  nginx proxy ───┼─────┼─►│  Routes    │  │     │  │  Slither   │  │
│  (injects key)  │     │  │  /api/v1/* │  │     │  │  Foundry   │  │
│                 │     │  └─────┬──────┘  │     │  │  LLM Audit │  │
└─────────────────┘     │        │         │     │  └────────────┘  │
                        │  ┌─────▼──────┐  │     └────────┬─────────┘
                        │  │  Services   │  │              │
                        │  └─────┬──────┘  │              │
                        └────────┼─────────┘              │
                                 │                        │
                   ┌─────────────┼────────────────────────┘
                   │             │              │
            ┌──────▼──────┐ ┌───▼────┐  ┌──────▼──────┐
            │ PostgreSQL  │ │ Redis  │  │  ChromaDB   │
            │   :5432     │ │ :6379  │  │  (vector)   │
            └─────────────┘ └────────┘  └─────────────┘
                                              │
                                     ┌────────▼────────┐
                                     │    LLM API      │
                                     │ (OpenAI/Anthr…) │
                                     └─────────────────┘
```

### Docker Compose Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `api` | python:3.11-slim | 8000 | FastAPI application server |
| `worker` | python:3.11-slim | — | Celery task workers (Slither, Foundry, LLM) |
| `postgres` | postgres:15 | 5432 | Primary database |
| `redis` | redis:7 | 6379 | Celery broker, cache, rate limiter |
| `frontend` | nginx:alpine | 3000 | React SPA + reverse proxy to API |
| `nginx-proxy` | nginx:alpine | 80/443 | Optional HTTPS termination (profile: `https`) |

### Key Design Decisions

- **JSON config over env vars** — Application settings live in `solidguard.json`; env vars only for infrastructure secrets and `${VAR}` interpolation.
- **Async everywhere** — FastAPI + SQLAlchemy async + HTTPX for non-blocking I/O.
- **Celery for long tasks** — Slither, Foundry, and LLM audits run in background workers with SSE progress streaming.
- **Provider abstraction** — Unified LLM client supporting OpenAI-compatible and Anthropic Messages APIs with automatic routing.

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
       │                          │
       │     RAG: ChromaDB ───────+  (SWC knowledge base)
       │
5. Generate Report           POST /projects/{id}/report
       │
6. Download HTML/PDF/Word    GET  /reports/{id}/download
```

### How It Works

1. **Upload** — Upload `.sol` files, `.zip`, or `.tar.gz` archives via API or web UI
2. **Slither** — Industry-standard static analysis detects known vulnerability patterns (reentrancy, overflow, access control, etc.)
3. **Foundry** — Fuzz testing generates random inputs to discover edge-case failures and invariant violations
4. **LLM Audit** — AI analyzes high-risk functions with RAG-enhanced context from the vulnerability knowledge base
5. **Report** — All findings aggregated, deduplicated, and exported as HTML/PDF/Word with severity coding

### RAG Strategy

| Step | Action | Purpose |
|------|--------|---------|
| **1. Summarize** | Compress contract to interface + state variables + function signatures | Reduce context window usage |
| **2. Extract** | Identify functions with external calls (`transfer`, `call`, `delegatecall`, etc.) | Focus on high-risk code paths |
| **3. Retrieve** | Embed function code, query ChromaDB for top-K similar known vulnerabilities | Inject known attack patterns |
| **4. Audit** | LLM receives summary + function body + similar vulnerabilities as context | Enhanced pattern recognition |

### False Positive Handling

Users mark individual Slither detections as false positive via the UI. Marked items are persisted in the database and automatically excluded from all subsequent analysis views and report generation.

---

## API Reference

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/projects` | Upload contracts (multipart/form-data) |
| `GET` | `/api/v1/projects` | List all projects |
| `GET` | `/api/v1/projects/{id}` | Get project detail |
| `GET` | `/api/v1/projects/{id}/files` | List project files |

### Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/projects/{id}/analyze` | Trigger Slither analysis |
| `GET` | `/api/v1/projects/{id}/analyses` | Get Slither results |
| `POST` | `/api/v1/projects/{id}/fuzz` | Trigger Foundry fuzz testing |
| `GET` | `/api/v1/projects/{id}/fuzz-results` | Get fuzz results |
| `POST` | `/api/v1/projects/{id}/llm-audit` | Trigger LLM deep audit |
| `GET` | `/api/v1/projects/{id}/llm-audit-results` | Get LLM audit results |

### Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/projects/{id}/report` | Generate audit report |
| `GET` | `/api/v1/projects/{id}/reports` | List project reports |
| `GET` | `/api/v1/reports/{id}/download` | Download report file |

### Knowledge Base

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/knowledge/sync` | Sync SWC Registry to DB + ChromaDB |
| `GET` | `/api/v1/vulnerabilities` | Search vulnerabilities (paginated) |

### Real-time Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/projects/{id}/events` | SSE event stream for live updates |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Returns `{"status": "ok"}` with Postgres/Redis checks |

> Full interactive API documentation: **http://localhost:8000/docs** (Swagger UI)

---

## Project Structure

```
SolidGuard/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI route handlers
│   │   │   ├── v1/                 # Versioned API endpoints (events, tasks)
│   │   │   ├── analysis.py         # Slither analysis routes
│   │   │   ├── detections.py       # Detection management routes
│   │   │   ├── fuzz.py             # Fuzz testing routes
│   │   │   ├── knowledge.py        # Knowledge base sync routes
│   │   │   ├── llm_audit.py        # LLM audit routes
│   │   │   ├── projects.py         # Project CRUD routes
│   │   │   ├── reports.py          # Report generation routes
│   │   │   ├── vulnerabilities.py  # Vulnerability search routes
│   │   │   └── router.py           # API router aggregation
│   │   ├── llm/                    # LLM module
│   │   │   ├── budget/             # Token budget management
│   │   │   ├── pipeline/           # LLM audit pipeline
│   │   │   ├── prompts/            # Prompt templates
│   │   │   ├── provider/           # Multi-provider routing
│   │   │   ├── rag/                # RAG retrieval logic
│   │   │   ├── schemas/            # LLM response schemas
│   │   │   ├── security/           # Input sanitization
│   │   │   └── config.py           # LLM config parser
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/               # Business logic engines
│   │   │   ├── engine/             # Core engines (slither, fuzz, llm_audit)
│   │   │   ├── infra/              # Infrastructure (storage)
│   │   │   └── templates/          # Report templates
│   │   ├── state/                  # Project state machine
│   │   ├── tasks/                  # Celery task definitions
│   │   ├── auth.py                 # API Key authentication
│   │   ├── celery_app.py           # Celery application factory
│   │   ├── config.py               # Settings from JSON config
│   │   ├── database.py             # DB engine & session factory
│   │   ├── dependencies.py         # FastAPI dependency injection
│   │   └── main.py                 # FastAPI application entry
│   ├── alembic/                    # Database migrations
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/                    # API client & hooks
│   │   ├── components/             # Shared components
│   │   ├── design-system/          # Design system (Button, Table, Tag, etc.)
│   │   ├── hooks/                  # Custom hooks (useSSE, useTaskProgress)
│   │   ├── layouts/                # AppShell, Header
│   │   ├── pages/                  # Page components
│   │   ├── stores/                 # Zustand state stores
│   │   ├── styles/                 # Global styles
│   │   └── utils/                  # Utilities (format, severity)
│   ├── Dockerfile                  # Multi-stage: node build → nginx serve
│   ├── nginx.conf                  # Reverse proxy + SPA fallback
│   └── package.json                # Node dependencies
├── docs/                           # Project documentation
│   ├── architecture/               # Architecture docs & audit reports
│   ├── design/                     # Design specs & feature proposals
│   ├── development/                # Development task specs
│   └── sprints/                    # Sprint plans & execution logs
├── tests/                          # Integration & security tests
├── docker/                         # Docker build files
│   ├── Dockerfile                  # Backend Docker image
│   └── nginx-proxy.conf            # HTTPS proxy config
├── docker-compose.yml              # Service orchestration
├── solidguard.json                 # Application configuration
├── solidguard.json.example         # Configuration template
├── .env.example                    # Environment variable template
└── .gitignore
```

---

## Documentation

All project documentation is organized under `docs/`:

| Directory | Contents |
|-----------|----------|
| `docs/architecture/` | System architecture, master blueprint, architecture audit report |
| `docs/sprints/` | Sprint plans (A–D) and execution logs |
| `docs/design/` | Design specs, feature proposals, refactor plans |
| `docs/development/` | Development task specs and prompts |

### Key Documents

| Document | Description |
|----------|-------------|
| [Master Blueprint](docs/architecture/master-blueprint.md) | Full architecture overview with 25 remediation items |
| [Architecture Audit Report](docs/architecture/architecture-audit.md) | Security & quality audit findings (4 Critical / 6 High / 9 Medium / 6 Low) |
| [LLM Call Chain Blueprint](docs/architecture/llm-call-chain-blueprint.md) | LLM module architecture design |
| [Frontend Rewrite Plan](docs/design/frontend-rewrite-plan.md) | Frontend redesign rationale and specs |
| [Sprint A–D Logs](docs/sprints/) | Sprint execution records and fix details |

---

## Development Guide

### Local Setup (without Docker)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start API (requires PostgreSQL + Redis running locally)
uvicorn app.main:app --reload --port 8000

# Start Celery worker
celery -A app.celery_app worker -B --loglevel=info

# Frontend
cd frontend
npm install
npm run dev                     # → http://localhost:5173
```

### Database Migrations

```bash
cd backend

# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### HTTPS Deployment

Enable the optional nginx reverse proxy with TLS:

```bash
docker compose --profile https up -d
```

Configure certificates in `docker/nginx-proxy.conf`.

---

## Testing

```bash
# Start all services
docker compose up -d

# Install test dependencies
cd tests
pip install -r requirements-test.txt

# Run all tests
pytest -v

# Run specific test suites
pytest test_integration.py -v    # Integration tests
pytest test_security.py -v       # Security tests
pytest test_engines.py -v        # Engine unit tests
pytest test_services.py -v       # Service unit tests
pytest test_api.py -v            # API endpoint tests
```

---

## FAQ

<details>
<summary><strong>Which LLM providers are supported?</strong></summary>

Any OpenAI-compatible API (OpenAI, Azure OpenAI, local models, Xiaomi Mimo, etc.) and the Anthropic Messages API. Set `"api": "openai"` or `"api": "anthropic-messages"` in `solidguard.json`. Multiple providers can be configured simultaneously.

</details>

<details>
<summary><strong>Can I use a local embedding model?</strong></summary>

Yes. Set `"api": "local"` in the `embedding` provider config to use `sentence-transformers` with `all-MiniLM-L6-v2`. No API key required — runs entirely locally.

</details>

<details>
<summary><strong>How does the SSE real-time progress work?</strong></summary>

When a task is triggered (Slither, Fuzz, LLM Audit), the frontend opens an SSE connection to `/api/v1/projects/{id}/events`. The backend polls for state changes and pushes events when new results are available. The frontend automatically refreshes data and shows toast notifications.

</details>

<details>
<summary><strong>How are false positives handled?</strong></summary>

Users mark individual Slither detections as false positive via the UI. Marked items are persisted in the database and automatically excluded from analysis result views and all subsequent report generation.

</details>

<details>
<summary><strong>What Solidity versions are supported?</strong></summary>

Solidity 0.4.x through 0.8.x, managed automatically via Slither and `solc-select`.

</details>

<details>
<summary><strong>How does RAG improve the LLM audit?</strong></summary>

Before auditing each function, the system embeds the function code and queries ChromaDB for the top-K most similar known vulnerabilities from the SWC Registry. These are injected into the LLM prompt as context, enabling the model to recognize patterns it might otherwise miss.

</details>

<details>
<summary><strong>How do I switch LLM providers?</strong></summary>

Edit `solidguard.json` and update the `providers.default` section. Supported API types: `"openai"` (OpenAI-compatible), `"anthropic-messages"` (Anthropic), `"local"` (embedding only). Changes take effect on next task execution — no restart required.

</details>

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure all tests pass before submitting a PR.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with** Python · FastAPI · Celery · PostgreSQL · Redis · ChromaDB · React · TypeScript · Slither · Foundry · Docker

</div>
