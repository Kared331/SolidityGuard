<div align="center">

# 🛡️ SolidiGuard

### Enterprise Solidity Smart Contract Audit Platform

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Automated vulnerability detection through **static analysis**, **fuzz testing**, and **LLM-powered deep audit** with RAG enhancement.

[Quick Start](#-quick-start) · [Features](#-features) · [API Reference](#-api-reference) · [Architecture](#-architecture) · [Development](#-development-guide)

</div>

---

## Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Architecture](#-architecture)
- [Audit Pipeline](#-audit-pipeline)
- [API Reference](#-api-reference)
- [Deployment Guide](#-deployment-guide)
- [Development Guide](#-development-guide)
- [Project Structure](#-project-structure)
- [FAQ](#-faq)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

| Feature | Description | Tool |
|---------|-------------|------|
| **Static Analysis** | Detect common Solidity vulnerabilities (reentrancy, overflow, etc.) | Slither |
| **Fuzz Testing** | Property-based testing with automatic test generation | Foundry |
| **LLM Deep Audit** | AI-powered code review with RAG-enhanced pattern matching | OpenAI / Anthropic |
| **False Positive Feedback** | Mark detections as false positive; auto-excluded from reports | Built-in |
| **Vulnerability Knowledge Base** | SWC Registry sync with vector search | Chroma |
| **Multi-format Reports** | Professional audit reports with severity coding | HTML / PDF / Word |

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/) installed
- API key for your LLM provider ([OpenAI](https://platform.openai.com), [Anthropic](https://console.anthropic.com), or compatible)
- API key for embeddings (OpenAI by default, or configure a local provider)

### 1. Clone and Configure

```bash
git clone https://github.com/your-org/solidiguard.git
cd solidiguard

# Copy environment template
cp .env.example .env
```

### 2. Set Environment Variables

Edit `.env` with your API keys:

```env
# Required: LLM Configuration
LLM_PROVIDER=openai              # openai | anthropic | local
LLM_API_KEY=sk-your-key-here
LLM_MODEL_NAME=gpt-4o

# Required: Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-your-key-here

# Optional: Override defaults
# LLM_BASE_URL=https://api.openai.com/v1
# EMBEDDING_BASE_URL=https://api.openai.com/v1
# CHROMA_PERSIST_DIR=./chroma_data
# RAG_TOP_K=5
```

### 3. Launch

```bash
docker-compose up -d
```

### 4. Access

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | [http://localhost:3000](http://localhost:3000) | Web interface |
| **API** | [http://localhost:8000](http://localhost:8000) | REST API |
| **API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI |

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection: `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | ✅ | — | Redis connection: `redis://host:6379/0` |
| `APP_PORT` | — | `8000` | API server port |
| `LLM_PROVIDER` | ✅ | `openai` | `openai` · `anthropic` · `local` |
| `LLM_API_KEY` | ✅ | — | API key for LLM provider |
| `LLM_MODEL_NAME` | ✅ | `gpt-4o` | Model identifier |
| `LLM_BASE_URL` | — | `https://api.openai.com/v1` | LLM API base URL (for local/proxy) |
| `EMBEDDING_PROVIDER` | ✅ | `openai` | `openai` · `local` (sentence-transformers) |
| `EMBEDDING_API_KEY` | ✅ | — | API key for embedding provider |
| `EMBEDDING_BASE_URL` | — | `https://api.openai.com/v1` | Embedding API base URL |
| `CHROMA_PERSIST_DIR` | — | `./chroma_data` | Chroma vector DB storage path |
| `RAG_TOP_K` | — | `5` | Number of similar vulnerabilities to retrieve |

---

## 🏗️ Architecture

### System Overview

```mermaid
graph LR
    subgraph Frontend["Frontend (React + AntD)"]
        UI[":3000"]
    end

    subgraph Backend["API Gateway (FastAPI)"]
        API[":8000"]
    end

    subgraph Workers["Celery Workers"]
        W1[File Processing]
        W2[Slither Analysis]
        W3[Foundry Fuzzing]
        W4[LLM Audit]
        W5[Knowledge Sync]
    end

    subgraph Storage["Data Layer"]
        PG[(PostgreSQL 15)]
        RD[(Redis)]
        CH[(Chroma)]
        FS[File System]
    end

    subgraph External["External Services"]
        LLM[LLM API]
        SWC[SWC Registry]
    end

    UI --> API
    API --> RD
    API --> PG
    RD --> Workers
    Workers --> PG
    Workers --> CH
    Workers --> LLM
    Workers --> SWC
    Workers --> FS
```

> 📐 Full architecture diagram: [`docs/architecture.svg.html`](docs/architecture.svg.html)

### Docker Compose Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `api` | python:3.11-slim | 8000 | FastAPI application |
| `worker` | python:3.11-slim | — | Celery task workers |
| `postgres` | postgres:15 | 5432 | Primary database |
| `redis` | redis:7 | 6379 | Celery broker & cache |
| `frontend` | nginx:alpine | 3000 | React SPA + API proxy |

---

## 🔄 Audit Pipeline

```mermaid
graph TD
    A["1️⃣ Upload Contracts"] -->|"POST /api/v1/projects"| B["2️⃣ Slither Static Analysis"]
    B -->|"POST /projects/{id}/analyze"| C["3️⃣ Foundry Fuzz Testing"]
    C -->|"POST /projects/{id}/fuzz"| D["4️⃣ LLM Deep Audit"]
    D -->|"POST /projects/{id}/llm-audit"| E["5️⃣ Generate Report"]
    E -->|"POST /projects/{id}/report"| F["📄 Download HTML/PDF/Word"]

    subgraph RAG["RAG Enhancement"]
        V[(SWC Registry)] -->|"Vector Search"| D
        CH[(Chroma DB)] -->|"Top-K Matches"| D
    end

    RAG -.->|"Context Injection"| D
```

> 📐 Pipeline diagram: [`docs/pipeline.svg.html`](docs/pipeline.svg.html)

### How It Works

1. **Upload** — User uploads `.sol` files, `.zip`, or `.tar.gz` archives
2. **Slither** — Industry-standard static analysis detects known vulnerability patterns
3. **Foundry** — Fuzz testing generates random inputs to find edge-case failures
4. **LLM Audit** — AI analyzes key functions with RAG-enhanced context from the vulnerability knowledge base
5. **Report** — All findings aggregated, polished by LLM, exported as HTML/PDF/Word

### RAG Strategy

Instead of feeding entire contracts into the LLM context window:

| Step | Action | Purpose |
|------|--------|---------|
| **1. Summary** | Compress contract to interface + state variables + signatures | Reduce context size |
| **2. Extract** | Identify functions with external calls (transfer, call, delegatecall, etc.) | Focus on high-risk code |
| **3. Retrieve** | Embed function code, query Chroma for top-K similar vulnerabilities | Inject known patterns |
| **4. Audit** | LLM receives summary + function + similar vulns → generates findings | Enhanced analysis |

---

## 📡 API Reference

### Projects

```
POST   /api/v1/projects                    Upload contracts (multipart/form-data)
GET    /api/v1/projects/{id}/files         List project files
```

### Analysis

```
POST   /api/v1/projects/{id}/analyze       Trigger Slither analysis
GET    /api/v1/projects/{id}/analyses      Get Slither results (filtered by FP)
POST   /api/v1/projects/{id}/fuzz          Trigger Foundry fuzzing
GET    /api/v1/projects/{id}/fuzz-results  Get fuzzing results
POST   /api/v1/projects/{id}/llm-audit     Trigger LLM audit
GET    /api/v1/projects/{id}/llm-audit-results  Get LLM audit results
```

### False Positive Management

```
POST   /api/v1/detections/{id}/mark-false-positive   Mark detection as FP
```

### Knowledge Base

```
POST   /api/v1/knowledge/sync              Sync SWC Registry to database + Chroma
GET    /api/v1/vulnerabilities             Search vulnerabilities (paginated)
       ?search=overflow&page=1&page_size=20
```

### Reports

```
POST   /api/v1/projects/{id}/report        Generate report
       Body: {"format": "html|pdf|word"}
GET    /api/v1/projects/{id}/reports       List project reports
GET    /api/v1/reports/{id}/download       Download report file
       ?format=html|pdf|word
```

### Health

```
GET    /health                             Returns {"status": "ok"}
```

> 📖 Full interactive API docs available at `http://localhost:8000/docs` (Swagger UI)

---

## 🚢 Deployment Guide

### Production Configuration

```bash
# Create production environment
cp .env.example .env.production

# Set secure values (never commit these!)
sed -i 's/LLM_API_KEY=.*/LLM_API_KEY=sk-your-production-key/' .env.production
sed -i 's/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=your-secure-password/' .env.production

# Launch with production config
docker-compose --env-file .env.production up -d
```

### Service Architecture

| Service | Internal Port | External Port | Scaling |
|---------|:------------:|:-------------:|---------|
| Frontend | 80 | 3000 | Horizontal (load balancer) |
| API | 8000 | 8000 | Horizontal (load balancer) |
| PostgreSQL | 5432 | 5432 | Read replicas |
| Redis | 6379 | 6379 | Sentinel / Cluster |
| Worker | — | — | Scale with queue depth |

### Monitoring

```bash
# Check service health
docker-compose ps

# View worker logs
docker-compose logs -f worker

# Check API health
curl http://localhost:8000/health
```

---

## 🛠️ Development Guide

### Local Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start API (requires PostgreSQL + Redis running)
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev                     # → http://localhost:5173
```

### Running Tests

```bash
# Start all services
docker-compose up -d

# Run integration tests
cd tests
pip install -r requirements-test.txt
pytest test_integration.py -v

# Run with coverage
pytest test_integration.py -v --tb=short
```

### Database Migrations

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Adding Custom Slither Detectors

1. Create your detector class following [Slither docs](https://github.com/crytic/slither/wiki/Adding-a-new-detector)
2. Mount the file into the worker container via `docker-compose.yml` volumes
3. Update the Slither command in `backend/app/tasks/run_slither.py`

---

## 📁 Project Structure

```
solidiguard/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI route handlers
│   │   │   ├── analysis.py         #   Slither analysis endpoints
│   │   │   ├── detections.py       #   False positive endpoints
│   │   │   ├── fuzz.py             #   Fuzzing endpoints
│   │   │   ├── knowledge.py        #   Knowledge sync endpoint
│   │   │   ├── llm_audit.py        #   LLM audit endpoints
│   │   │   ├── projects.py         #   Project upload endpoints
│   │   │   ├── reports.py          #   Report generation endpoints
│   │   │   ├── vulnerabilities.py  #   Vulnerability DB query
│   │   │   └── router.py           #   Router aggregation
│   │   ├── services/               # Business logic
│   │   │   ├── chroma_client.py    #   Chroma vector DB client
│   │   │   ├── embedding.py        #   Embedding provider abstraction
│   │   │   ├── llm_client.py       #   LLM provider abstraction
│   │   │   ├── report_generator.py #   Report generation engine
│   │   │   └── templates/          #   Jinja2 report templates
│   │   ├── tasks/                  # Celery task definitions
│   │   │   ├── generate_report.py  #   Report generation task
│   │   │   ├── process_upload.py   #   File extraction task
│   │   │   ├── run_fuzzer.py       #   Foundry fuzzing task
│   │   │   ├── run_llm_audit.py    #   LLM audit task (RAG)
│   │   │   └── sync_swc.py         #   SWC Registry sync task
│   │   ├── models.py               # SQLAlchemy ORM models (8 tables)
│   │   ├── database.py             # DB engine & session factory
│   │   ├── celery_app.py           # Celery configuration
│   │   ├── config.py               # Environment variable loading
│   │   └── main.py                 # FastAPI application entry
│   ├── alembic/                    # Database migrations (8 versions)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.ts           # Axios HTTP client
│   │   ├── pages/
│   │   │   ├── UploadPage.tsx      # Contract upload (drag & drop)
│   │   │   ├── ProjectDetailPage.tsx # Analysis dashboard + FP marking
│   │   │   ├── ReportPage.tsx      # Report generation & download
│   │   │   └── VulnerabilitiesPage.tsx # SWC vulnerability browser
│   │   ├── App.tsx                 # Layout shell (Header + Nav)
│   │   └── main.tsx                # React Router configuration
│   ├── Dockerfile                  # Multi-stage: node → nginx
│   └── nginx.conf                  # Reverse proxy + SPA fallback
├── tests/
│   ├── test_integration.py         # 18 integration test cases
│   ├── conftest.py                 # pytest fixtures
│   └── fixtures/                   # Test Solidity contracts
├── docker-compose.yml              # 5-service orchestration
├── .env.example                    # Environment variable template
└── README.md
```

---

## 🗄️ Database Schema

| Table | Purpose | Sprint |
|-------|---------|--------|
| `projects` | Uploaded project metadata | 1 |
| `project_files` | Individual file tracking | 1 |
| `analysis_results` | Slither raw output storage | 2 |
| `detections` | Individual Slither detections | 3 |
| `false_positive_feedbacks` | User FP markings | 3 |
| `vulnerability_entries` | SWC Registry knowledge base | 4 |
| `fuzzing_results` | Foundry fuzz test output | 5 |
| `llm_audit_results` | LLM audit findings | 6 |
| `reports` | Generated report metadata | 7 |

---

## ❓ FAQ

<details>
<summary><strong>Which LLM providers are supported?</strong></summary>

OpenAI, Anthropic, and any OpenAI-compatible local model (via `LLM_BASE_URL`). Set `LLM_PROVIDER` to `openai`, `anthropic`, or `local`.

</details>

<details>
<summary><strong>Can I use a local embedding model?</strong></summary>

Yes. Set `EMBEDDING_PROVIDER=local` to use `sentence-transformers` with `all-MiniLM-L6-v2`. No API key required.

</details>

<details>
<summary><strong>How are false positives handled?</strong></summary>

Users mark individual Slither detections as false positive via the UI. Marked items are automatically excluded from analysis result views and all subsequent report generation.

</details>

<details>
<summary><strong>What Solidity versions are supported?</strong></summary>

Solidity 0.4.x through 0.8.x, managed automatically via Slither and `solc-select`.

</details>

<details>
<summary><strong>Can I add custom Slither detectors?</strong></summary>

Yes. Create a custom detector class per [Slither documentation](https://github.com/crytic/slither/wiki/Adding-a-new-detector), mount it into the worker container, and update the Slither command in `run_slither.py`.

</details>

<details>
<summary><strong>How does RAG improve the LLM audit?</strong></summary>

Before auditing each function, the system embeds the function code and queries Chroma for the top-K most similar known vulnerabilities from the SWC Registry. These are injected into the LLM prompt as context, enabling the model to recognize patterns it might otherwise miss.

</details>

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Open a Pull Request

### Standards

| Area | Standard |
|------|----------|
| Python | PEP 8, type hints required |
| TypeScript | Strict mode, ESLint |
| Tests | All API endpoints must have integration tests |
| Database | Changes via Alembic migrations only |
| Commits | Conventional commits (`feat:`, `fix:`, `docs:`) |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with** Python · FastAPI · Celery · PostgreSQL · Redis · Chroma · React · Ant Design · Slither · Foundry · Docker

</div>
