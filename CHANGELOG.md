# CHANGELOG

SolidGuard 项目更新说明。

本文档记录从 GitHub 初始提交（2026-06-05）至今的所有重大变更。

---

## [Unreleased] — 2026-06-05 ~ 2026-07-21

> 从初始提交到当前工作区的全部变更。涵盖架构重构、安全修复、功能新增、前端重写、测试扩展。

---

### 🏗️ 架构重构

#### 后端模块化

- **ORM 模型拆分**：`models.py`（单文件 155 行）→ `models/` 目录，按实体拆分为 `project.py`、`analysis.py`、`audit.py`、`feedback.py`、`knowledge.py`、`report.py`
- **服务层重组**：`services/` 从 4 个平铺文件重组为 `engine/`（核心引擎）+ `infra/`（基础设施）+ 10+ 个独立服务文件
- **LLM 模块独立**：从散装 `llm_client.py` 长出完整的 `llm/` 子系统，含 7 个子目录：
  - `budget/` — Token 预算管理
  - `pipeline/` — 审计流水线（含流式 SSE 推送）
  - `prompts/` — YAML 模板 + 注册表 + 加载器
  - `provider/` — 多 Provider 路由（OpenAI / Anthropic / 本地）
  - `rag/` — RAG 检索 + 嵌入抽象 + 健康检查
  - `schemas/` — 审计输出与 Prompt 上下文 Schema
  - `security/` — 输入消毒 + 输出校验
- **API 版本化**：新增 `api/v1/` 目录（`events.py`、`tasks.py`）
- **Pydantic Schema 层**：新增 `schemas/` 目录（10 个文件），类型安全的请求/响应定义
- **状态机**：新增 `state/project_state.py`，项目生命周期状态管理
- **依赖注入**：新增 `dependencies.py`

#### 前端重构

- **页面模块化**：4 个单文件页面 → 6 个功能模块目录（`Dashboard/`、`LLMAudit/`、`ProjectDetail/`、`Report/`、`Upload/`、`Vulnerabilities/`），每个页面拆分为多个子组件 + CSS Module
- **设计系统**：移除 Ant Design，自建 `design-system/`（`components/`、`icons/`、`tokens/`、`index.ts`），包体积从 ~1.2MB 降至 <50KB
- **状态管理**：引入 Zustand（`useAppStore`、`useAuditDetailStore`、`useToastStore`）
- **数据获取**：引入 TanStack React Query + 自定义 hooks（`useAnalyses`、`useAuditResults`、`useFuzzResults`、`useProjects`、`useReports`、`useVulnerabilities`）
- **API 层**：新增 `types.ts`（类型定义）、`queryKeys.ts`（缓存键管理）
- **布局拆分**：`App.tsx` → `layouts/AppShell` + `layouts/Header`
- **公共 Hooks**：新增 `useSSE`（实时事件订阅）、`useTaskProgress`（任务进度追踪）
- **公共组件**：新增 `components/Toast`

#### 配置系统重构

- **从环境变量到 JSON 配置**：应用配置从 `.env` 环境变量迁移到 `solidguard.json` JSON 配置文件，环境变量仅用于 Docker 基础设施和 `${VAR}` 插值
- **多 Provider 配置**：支持 `providers.default`、`providers.xiaomi`、`providers.embedding` 多 provider 路由
- **新增文件**：`solidguard.json`、`solidguard.json.example`

---

### 🔴 安全修复（Sprint A — 7/7 完成）

| Fix | 描述 | 影响 |
|-----|------|------|
| #1 | **Zip Slip / Tar Slip** — 归档解压路径遍历防护修复，改为逐成员校验后解压 | CRITICAL |
| #2 | **SSE 认证绕过** — `events_router` 注册时添加 `verify_api_key` 依赖 | CRITICAL |
| #3 | **路由前缀冲突** — 各路由文件去掉重复前缀，修复大量 404 | CRITICAL |
| #4 | **报告路径遍历** — 添加 `resolved_path.relative_to(reports_base)` 校验 | CRITICAL |
| #5 | **LLM Prompt 注入** — 实现 `InputSanitizer` 类，8 种注入模式检测 + token 感知截断 | HIGH |
| #6 | **前端 API Key 泄露** — API Key 改由 nginx 注入，前端不再硬编码 | HIGH |
| #7 | **FP 项目作用域** — 误报反馈关联到项目级别，跨项目不再互相影响 | HIGH |

---

### 🟡 基础设施加固（Sprint B — 8/8 完成）

| Fix | 描述 | 影响 |
|-----|------|------|
| #6 | **数据库外键索引** — 所有 FK 列添加 `index=True`，6 个新索引 | HIGH |
| #7 | **清理任务级联删除** — 按 FK 依赖顺序级联删除关联记录 | HIGH |
| #9 | **CORS 配置** — 添加 `CORSMiddleware`，来源通过 `CORS_ORIGINS` 配置 | HIGH |
| #11 | **速率限制** — 集成 SlowAPI，默认 60 req/min，Redis 存储 | HIGH |
| #12 | **SSE 轮询优化** — 动态调整轮询间隔 | MEDIUM |
| #13 | **线程安全单例** — ChromaDB 客户端和 Embedding 使用线程锁 | MEDIUM |
| #14 | **Embedding 模型名配置化** — 不再硬编码模型名 | MEDIUM |
| #16 | **数据库连接池** — 添加 `poolSize`、`maxOverflow`、`poolRecycle` 配置 | MEDIUM |
| — | **str(Exception) bug** — 修复 6 个 Celery 任务中的 `str(Exception)` → `str(e)` | — |

---

### 🟢 可靠性与质量（Sprint C — 8/8 完成）

| Fix | 描述 | 影响 |
|-----|------|------|
| #17 | **LLM JSON 解析加固** — 4 阶段解析管道（直接解析 → markdown 提取 → 正则回退 → 日志警告） | MEDIUM |
| #18 | **报告 LLM 验证** — `polish_with_llm` 结果结构校验 | MEDIUM |
| #19 | **状态机 DB 约束** — CHECK 约束限制 status 值 + 乐观锁 version 列 | MEDIUM |
| #20 | **.gitignore 清理** — 移除不应追踪的文件 | LOW |
| #21 | **死代码删除** — 移除 `models_old.py` | LOW |
| #22 | **健康检查扩展** — PostgreSQL + Redis 双检查，超时 3s，返回 `degraded` 状态 | LOW |
| #23 | **Docker 文件权限** — 容器内使用非 root 用户 `1000:1000` | LOW |
| #24 | **优雅停机** — FastAPI shutdown event 关闭数据库连接 | LOW |

---

### 🧪 测试（Sprint D — 72/72 通过）

| 测试文件 | 测试数 | 覆盖范围 |
|----------|--------|----------|
| `test_services.py` | 14 | project_service / detection_service / analysis_service |
| `test_engines.py` | 22 | upload engine / llm_audit engine / report engine |
| `test_security.py` | 16 | 路径遍历 / Prompt 注入 / Zip Slip / FP 作用域 |
| `test_api.py` | 12 | Health / Upload / Files / Analyze / Mark-FP |
| `test_integration.py` | 18 | 端到端集成测试（原有） |
| **合计** | **72** | — |

- 新增 `pytest.ini` 配置
- `conftest.py` 从基础扩展到 302+ 行，含完整 fixtures 体系

---

### ✨ 功能新增

#### LLM 模块

- **多 Provider 路由** — `provider/` 支持 OpenAI 兼容 API + Anthropic Messages API + 本地模型，含 `provider_registry.py`（自动路由）和 `provider_stats.py`（调用统计）
- **Token 预算管理** — `budget/token_budget.py`，跟踪每个项目的 token 消耗和调用次数，可配置上限（默认 500,000 tokens / 100 次调用）
- **审计流水线** — `pipeline/audit_pipeline.py` + `stream.py`，结构化审计流程 + 流式 SSE 推送
- **Prompt 模板系统** — YAML 模板（`contract_summary.yaml`、`function_audit.yaml`、`report_polish.yaml`、`system_personas.yaml`）+ 注册表 + 加载器
- **输入安全防护** — `security/input_sanitizer.py`（8 种注入模式检测 + token 感知截断）+ `output_validator.py`（LLM 输出校验）
- **RAG 健康检查** — `rag/health_check.py`

#### 后端

- **SSE 实时事件** — `api/v1/events.py`，前端通过 `useSSE` hook 订阅
- **任务流水线** — `tasks/pipeline.py`，编排多步骤审计任务
- **HTTPS 反向代理** — `docker/nginx-proxy.conf` + `docker-compose.yml` 中的 `nginx-proxy` 服务（profile: `https`）
- **输入校验增强** — 自定义 `RequestValidationError` handler，含 multipart body 解析 + 详细日志

#### 前端

- **Dashboard 页面** — `DashboardPage.tsx` + `ProjectCard.tsx`，项目总览与快速操作
- **LLM 审计详情页** — 5 个子组件：`ExecutiveSummary`、`RiskOverview`、`DetailedFindings`、`RecommendationsSummary`、`LLMAuditPage`
- **CSS Modules** — 所有页面样式隔离（`.module.css`）

---

### 📦 数据库迁移

| 迁移 | 内容 |
|------|------|
| `009_add_project_status` | 项目状态字段 |
| `010_add_feedback_project_scope` | 误报反馈项目级作用域 |
| `011_add_foreign_key_indexes` | 外键索引优化（6 个索引） |
| `012_add_state_machine_constraints` | 状态机 CHECK 约束 + 乐观锁 version 列 |

---

### 🔄 依赖更新

| 包 | 变更 |
|----|------|
| FastAPI | 0.109 → 0.128+ |
| `slowapi` | 新增（速率限制） |
| `tenacity` | 新增（重试机制） |
| `pydantic-settings` | 新增（配置管理） |
| `zustand` | 新增（前端状态管理） |
| `@tanstack/react-query` | 新增（前端数据获取） |
| Ant Design | 移除（替换为自建设计系统） |

---

### 📚 文档

- **架构审查报告** — `docs/architecture/architecture-audit.md`（25 项漏洞，4 Critical / 6 High / 9 Medium / 6 Low）
- **Master Blueprint** — `docs/architecture/master-blueprint.md`（MetaGPT Architect Bob 生成，54KB）
- **LLM 调用链蓝图** — `docs/architecture/llm-call-chain-blueprint.md`
- **前端重写计划** — `docs/design/frontend-rewrite-plan.md`（技术选型 + 实施方案）
- **Sprint A–D 执行日志** — `docs/sprints/`（含修复清单与详细改动）
- **Sprint 1–3 设计文档** — LLM 稳定性 / Embedding 重构 / 前端重设计
- **README.md** — 全面重写，反映当前项目实际状态

---

### 🗂️ 文件变更统计

```
修改:  46 个文件（1952 增 / 2545 删）
新增:  40+ 个文件（新模块 / 新架构 / 新测试）
删除:  5 个文件（被重构替代）
迁移:  4 个 Alembic 版本
```

---

## [Initial] — 2026-06-05

- 初始提交：SolidityGuard
- 基础功能：Slither 静态分析 + Foundry 模糊测试 + LLM 审计 + RAG 增强 + 报告生成
- 技术栈：FastAPI + Celery + PostgreSQL + Redis + ChromaDB + React + Ant Design + Docker Compose
- 仓库地址：[Kared331/SolidityGuard](https://github.com/Kared331/SolidityGuard)
