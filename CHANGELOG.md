# CHANGELOG

SolidGuard 项目更新说明。

本文档记录从 GitHub 初始提交（2026-06-05）至今的所有重大变更。

***

## [Unreleased]

> 待规划变更。

### 2026-10-18 · 审计完整性 P5（D1 决策）

- **语料**：5 个仓库 / 176 文件 / 1759 函数，commit 锁定（`docs/evidence/corpus.lock.json`）；提取回归 `1759 = 1759`（漏/噪 0）。
- **实测**：关键词过滤丢弃率 **20.9%**（periphery 4.2% → openzeppelin 26.8%）。
- **决策**：保留过滤，但把过滤项作为 `filtered / keyword_filter` 写进账本；恒等式扩为四项，新增 `audit_runs.functions_filtered`（迁移 014），报告新增 "Filtered (keyword)" 行。
- **理由**：若只保留过滤，分母会从 1759 缩到 1391，报告会显示"100% 覆盖"——正是 P1 消灭过的静默丢失。
- **测试**：158 单测（+2）。

### 2026-10-18 · 审计完整性 P4（知识库）

- **SWC 离线快照**：37 条随代码入库（`services/engine/data/swc_registry.json`），默认同步不再联网；`?refresh=true` 才访问已归档的上游仓库，且结果必须通过条数/字段校验。
- **版本化**：`kb_version = swc-<hash8>`（实测 `swc-52c82b8a`）写入 `audit_runs`，报告显示 model / prompt / KB 三版本。
- **修复静默缺陷**：Chroma 从未写入 metadata，检索标题恒为 `Unknown`；已补 `metadatas` 并重同步。
- **检索实测**：10 条人工 query，top-1 命中 4/10、top-3 7/10；README 删除"显著提升检出率"的表述，改为"效果未验证"。
- **测试**：156 单测（+11）。

### 2026-10-18 · 审计完整性 P3（Fuzzer）
- **重写 `services/engine/fuzzer.py`**：旧实现生成的测试必然编译失败（无 import、无构造参数、签名不符），且编译失败被当作"0 失败"。新实现按真实签名生成、临时目录执行、输出截断 64KB。
- **唯一不变量**：ERC-20 供给守恒（`totalSupply` + 余额 getter + `transfer` + 单参支出函数）。不可推导时返回 `no_invariant_derivable`，不生成恒真测试。
- **实测**：`VulnerableToken` 产出真实失败（`assertion failed: 0 != 1`，`withdraw / supply_conservation`）；`SimpleToken` 正确跳过；`uploads/47` 不再被污染。
- **范围声明**：这是守恒探针，不是通用漏洞检测器；**重入不在能力内**。
- **测试**：145 单测（+7）。

### 2026-10-18 · 审计完整性 P0–P2

- **提取层**：新增 `services/engine/solidity_units.py`（掩码注释/字符串 + 括号配对），替换正则+关键词白名单。实测 57 个真实文件：提取单元 1896 = 参考真值，漏/噪 0；`constructor`/`receive`/`fallback` 不再被跳过。旧实现的问题记录于 `docs/evidence/extraction-baseline.md`。
- **审计账本**：新增 `audit_runs` 表与 `llm_audit_results.audit_run_id`（迁移 013）。两条恒等式可断言：`files_total = processed + unreadable`、`functions_extracted = audited + skipped + failed`。
- **降级可见**：预算耗尽/RAG 失败/LLM 异常/解析失败均写入单元状态与原因；`severity="unknown"` 出口删除，失败不再伪装成 finding。
- **报告**：新增"Audit Coverage & Integrity"段与降级横幅；LLM findings 只取最新一次 run，修复重复审计导致报告重复计入的问题。
- **清理**：cleanup 补 `audit_runs` 删除（FK 顺序）。
- **测试**：138 单测（+25）/ 20 集成 / 7 性能全绿；E2E 项目 #47 验证账本与报告一致。
- **对外材料**：README 删除无出处的 `210s → 70s`，改为 mock 基准实测并标注口径。

***

## [3.0.1] — 2026-09-03

> 知识库同步链路修复：SWC 同步端点 500、每周自动同步、前端手动同步入口。测试基准：95/95 单元测试通过。

### 🔧 修复与增强

- **修复 `POST /api/v1/knowledge/sync` 端点 500** — celery producer pool 在线程内首次建连丢失 broker hostname（回退 localhost 被拒）；新增 `_apply_with_connection` 显式连接发布，覆盖 task_dispatcher 四个流水线、process_upload、SWC 同步全部 API 侧派发点

- **SWC 知识库每周自动同步** — celery beat 新增 `sync-swc-weekly`（周一 03:10 UTC）；配置 `GITHUB_TOKEN` 后全量拉取不再撞未认证 60/hr 限额

- **知识库页「同步数据」按钮** — 手动触发同步（经 nginx 注入 X-API-Key，无前端泄 key 风险）

- **测试适配** — 派发路径 mock `_apply_with_connection`，断言更新为 `apply_async`；基准保持 95/95

***

## [3.0.0] — 2026-09-02

> 企业级稳定性打磨（P1/P2/P3）、性能压测与优化（P4）、启动体验与知识库修复。测试基准：95/95 单元测试通过。

***

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

***

### 🔴 安全修复（Sprint A — 7/7 完成）

| Fix | 描述                                                               | 影响       |
| --- | ---------------------------------------------------------------- | -------- |
| #1  | **Zip Slip / Tar Slip** — 归档解压路径遍历防护修复，改为逐成员校验后解压                | CRITICAL |
| #2  | **SSE 认证绕过** — `events_router` 注册时添加 `verify_api_key` 依赖         | CRITICAL |
| #3  | **路由前缀冲突** — 各路由文件去掉重复前缀，修复大量 404                                | CRITICAL |
| #4  | **报告路径遍历** — 添加 `resolved_path.relative_to(reports_base)` 校验     | CRITICAL |
| #5  | **LLM Prompt 注入** — 实现 `InputSanitizer` 类，8 种注入模式检测 + token 感知截断 | HIGH     |
| #6  | **前端 API Key 泄露** — API Key 改由 nginx 注入，前端不再硬编码                  | HIGH     |
| #7  | **FP 项目作用域** — 误报反馈关联到项目级别，跨项目不再互相影响                             | HIGH     |

***

### 🟡 基础设施加固（Sprint B — 8/8 完成）

| Fix | 描述                                                                      | 影响     |
| --- | ----------------------------------------------------------------------- | ------ |
| #6  | **数据库外键索引** — 所有 FK 列添加 `index=True`，6 个新索引                             | HIGH   |
| #7  | **清理任务级联删除** — 按 FK 依赖顺序级联删除关联记录                                        | HIGH   |
| #9  | **CORS 配置** — 添加 `CORSMiddleware`，来源通过 `CORS_ORIGINS` 配置                | HIGH   |
| #11 | **速率限制** — 集成 SlowAPI，默认 60 req/min，Redis 存储                            | HIGH   |
| #12 | **SSE 轮询优化** — 动态调整轮询间隔                                                 | MEDIUM |
| #13 | **线程安全单例** — ChromaDB 客户端和 Embedding 使用线程锁                              | MEDIUM |
| #14 | **Embedding 模型名配置化** — 不再硬编码模型名                                         | MEDIUM |
| #16 | **数据库连接池** — 添加 `poolSize`、`maxOverflow`、`poolRecycle` 配置               | MEDIUM |
| —   | **str(Exception) bug** — 修复 6 个 Celery 任务中的 `str(Exception)` → `str(e)` | —      |

***

### 🟢 可靠性与质量（Sprint C — 8/8 完成）

| Fix | 描述                                                             | 影响     |
| --- | -------------------------------------------------------------- | ------ |
| #17 | **LLM JSON 解析加固** — 4 阶段解析管道（直接解析 → markdown 提取 → 正则回退 → 日志警告） | MEDIUM |
| #18 | **报告 LLM 验证** — `polish_with_llm` 结果结构校验                       | MEDIUM |
| #19 | **状态机 DB 约束** — CHECK 约束限制 status 值 + 乐观锁 version 列            | MEDIUM |
| #20 | **.gitignore 清理** — 移除不应追踪的文件                                  | LOW    |
| #21 | **死代码删除** — 移除 `models_old.py`                                 | LOW    |
| #22 | **健康检查扩展** — PostgreSQL + Redis 双检查，超时 3s，返回 `degraded` 状态     | LOW    |
| #23 | **Docker 文件权限** — 容器内使用非 root 用户 `1000:1000`                   | LOW    |
| #24 | **优雅停机** — FastAPI shutdown event 关闭数据库连接                      | LOW    |

***

### 🧪 测试（Sprint D — 72/72 通过）

| 测试文件                  | 测试数    | 覆盖范围                                                      |
| --------------------- | ------ | --------------------------------------------------------- |
| `test_services.py`    | 14     | project_service / detection_service / analysis_service |
| `test_engines.py`     | 22     | upload engine / llm_audit engine / report engine         |
| `test_security.py`    | 16     | 路径遍历 / Prompt 注入 / Zip Slip / FP 作用域                      |
| `test_api.py`         | 12     | Health / Upload / Files / Analyze / Mark-FP               |
| `test_integration.py` | 18     | 端到端集成测试（原有）                                               |
| **合计**                | **72** | —                                                         |

- 新增 `pytest.ini` 配置

- `conftest.py` 从基础扩展到 302+ 行，含完整 fixtures 体系

***

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

***

### 📦 数据库迁移

| 迁移                                  | 内容                           |
| ----------------------------------- | ---------------------------- |
| `009_add_project_status`            | 项目状态字段                       |
| `010_add_feedback_project_scope`    | 误报反馈项目级作用域                   |
| `011_add_foreign_key_indexes`       | 外键索引优化（6 个索引）                |
| `012_add_state_machine_constraints` | 状态机 CHECK 约束 + 乐观锁 version 列 |

***

### 🔄 依赖更新

| 包                       | 变更             |
| ----------------------- | -------------- |
| FastAPI                 | 0.109 → 0.128+ |
| `slowapi`               | 新增（速率限制）       |
| `tenacity`              | 新增（重试机制）       |
| `pydantic-settings`     | 新增（配置管理）       |
| `zustand`               | 新增（前端状态管理）     |
| `@tanstack/react-query` | 新增（前端数据获取）     |
| Ant Design              | 移除（替换为自建设计系统）  |

***

### 📚 文档

- **架构审查报告** — `docs/architecture/architecture-audit.md`（25 项漏洞，4 Critical / 6 High / 9 Medium / 6 Low）

- **Master Blueprint** — `docs/architecture/master-blueprint.md`（MetaGPT Architect Bob 生成，54KB）

- **LLM 调用链蓝图** — `docs/architecture/llm-call-chain-blueprint.md`

- **前端重写计划** — `docs/design/frontend-rewrite-plan.md`（技术选型 + 实施方案）

- **Sprint A–D 执行日志** — `docs/sprints/`（含修复清单与详细改动）

- **Sprint 1–3 设计文档** — LLM 稳定性 / Embedding 重构 / 前端重设计

- **README.md** — 全面重写，反映当前项目实际状态

***

### 🔵 企业级稳定性与运维打磨（Phase 1-3 — P0/P1/P2，2026-08-28 ~ 2026-09-01）

> 依据 `MODIFICATION_BLUEPRINT.md` 蓝图，从「核心链路可用」推进到「企业级本地工具」标准。3 阶段共 25 项交付，commit `9a3112c`。

#### P0 阻塞修复（阶段一，6/6 完成）

| 编号   | 名称                                             | 关键文件                                                      |
| ---- | ---------------------------------------------- | --------------------------------------------------------- |
| P0-1 | 激活集成测试套件（fixture 补齐）                           | `tests/test_integration.py`、`pytest.ini`                  |
| P0-2 | LLM Provider 重试机制（tenacity，429/5xx 重试，401 不重试） | `llm/provider/openai_provider.py`、`anthropic_provider.py` |
| P0-3 | LLM 调用独立限流（Semaphore(maxConcurrentCalls)）      | `llm/sync_wrapper.py`、`llm/config.py`                     |
| P0-4 | sync_wrapper 事件循环复用修复（常驻守护线程事件循环）             | `llm/sync_wrapper.py`                                     |
| P0-5 | Celery 失败态干净回传与失败原因可观测（S4）                     | `tasks/generate_report.py` 等全部任务                          |
| P0-6 | report_generator 回归测试固化                       | `tests/`                                                  |

#### P1 达标差距项（阶段二，11/11 完成）

| 编号    | 名称                                             | 关键文件                                    |
| ----- | ---------------------------------------------- | --------------------------------------- |
| P1-1  | Celery 任务幂等（重复触发不产生重复检测）                       | `services/task_dispatcher.py`、`tasks/*` |
| P1-2  | 前端 Error Boundary                              | `frontend/src/components/`、`main.tsx`   |
| P1-3  | axios 全局错误拦截                                   | `frontend/src/api/client.ts`            |
| P1-4  | Provider AsyncClient 统一关闭（含 S7 生命周期统一）         | `main.py`、`celery_app.py`               |
| P1-5  | Compose 运维加固（restart policy + redis env_file） | `docker-compose.yml`                    |
| P1-6  | 配置规范化与教训固化（单一事实来源）                             | `.env.example`、`.gitignore`、`config.py` |
| P1-7  | Token 预算持久化（S1，重启不清零）                          | `llm/budget/token_budget.py`            |
| P1-8  | SSE 断线重连与降级轮询（S2）                              | `hooks/useSSE.ts`                       |
| P1-9  | worker 优雅关闭超时匹配任务时长（S5）                        | `celery_app.py`                         |
| P1-10 | 生产路径接入 AuditFindingSchema 校验（S6）               | `services/engine/llm_audit.py`          |
| P1-11 | README 真实化 + TROUBLESHOOTING（S8）               | `README.md`                             |

#### P2 打磨项（阶段三，8/8 完成）

| 编号   | 名称                                                   | 关键文件                                               |
| ---- | ---------------------------------------------------- | -------------------------------------------------- |
| P2-1 | LLMObservability 指标加锁（`threading.Lock` 线程安全）         | `llm/provider/provider_stats.py`                   |
| P2-2 | 线程池-信号量边界协调（embedding 只锁网络 I/O）                      | `services/embedding.py`                            |
| P2-3 | 前端长任务进度展示（SSE progress + 进度条 UI）                     | `hooks/useTaskProgress.ts`、`ProjectDetailPage.tsx` |
| P2-4 | lifespan 迁移（`@app.on_event` → `asynccontextmanager`） | `main.py`                                          |
| P2-5 | 前端上传大小预校验（50MB 与 nginx 对齐）                           | `pages/Upload/UploadPage.tsx`                      |
| P2-6 | manage.ps1 doctor 自检子命令（4 项检查）                       | `manage.ps1`                                       |
| P2-7 | 前端速赢包（`lang="zh-CN"` + `alert()` → Toast）            | `index.html`、`LLMAuditPage.tsx`                    |
| P2-8 | 解压安全测试固化 + tar 符号链接加固（S3 拮余）                         | `services/engine/upload.py`、`tests/`               |

#### 测试与验证

- 单测：91 → **95 项全绿**（新增 P2-8 的 4 项 tar 安全回归测试）

- 集成测试：20 项（P0-1 激活，服务不可达时自动 SKIP）

- 前端构建：`tsc && vite build` 通过

- 端到端：上传 → 分析 → LLM 审计 → 报告 → 下载 全链路 HTTP 200

- 5 容器编排启动；`/health`、`/docs` 正常

***

### 🚀 性能压测与优化（Phase 4 — 2026-09-01）

> 基于引擎级基线压测识别真实瓶颈并实施函数级 LLM 并行优化。详细数据见 `MODIFICATION_BLUEPRINT.md` 第 11 章。

#### P4-1 基线压测（mock LLM/embedding）

| 场景                      | 耗时                            | 结论                         |
| ----------------------- | ----------------------------- | -------------------------- |
| A 单文件 2 函数 + 即时 mock    | 1.5ms                         | 纯逻辑开销可忽略                   |
| B 5 文件 × 2 函数 + 即时 mock | 串 2.7ms / 并 3.4ms (0.77x)     | 小任务下 ThreadPool 开销抵消收益（预期） |
| C 单文件 2 函数 + LLM 50ms   | 181.3ms                       | **LLM 串行调用是真实瓶颈**          |
| D 5 文件并行 + LLM 50ms     | 935.7ms → 179.4ms (**5.22x**) | 文件级并行接近理论上限                |
| E 批量 vs 逐个 embedding    | 25.0ms / 308.0ms (**12.32x**) | `_BATCH_LIMIT=32` 批量化收益巨大  |
| F 单文件 10 函数串行（基线）       | 689.6ms                       | 单文件多函数串行瓶颈                 |

#### P4-3 优化：函数级 LLM 并行

**改动**：`backend/app/services/engine/llm_audit.py`

- 提取 `_audit_single_function()` 辅助方法（线程安全，token_budget check 内置 `threading.Lock`）

- `execute_single_file` 内当 `len(key_functions) > _PARALLEL_FUNC_THRESHOLD(5)` 时启用 `ThreadPoolExecutor(max_workers=5)`

- 阈值取 5：与全局 LLM `Semaphore(maxConcurrentCalls=5)` 对齐，避免多文件嵌套场景线程膨胀

#### P4-3 验证

| 场景                    | P4-3 前  | P4-3 后  | 加速比         |
| --------------------- | ------- | ------- | ----------- |
| F 单文件 5 函数（≤阈值，串行路径）  | —       | 366.4ms | 守护串行 ✓      |
| G 单文件 10 函数（>阈值，并行路径） | 689.6ms | 181.8ms | **3.79x** ✓ |

#### 回归验证

- 全量单测：**95/95 通过**（27 deselected，含 7 perf + 20 integration）

- 7 个 perf 场景全绿（含 P4-3 前后对比守护）

- 无功能回归

***

### 🗂️ 文件变更统计

```
修改:  46 个文件（1952 增 / 2545 删）
新增:  40+ 个文件（新模块 / 新架构 / 新测试）
删除:  5 个文件（被重构替代）
迁移:  4 个 Alembic 版本
```

***

## [Initial] — 2026-06-05

- 初始提交：SolidityGuard

- 基础功能：Slither 静态分析 + Foundry 模糊测试 + LLM 审计 + RAG 增强 + 报告生成

- 技术栈：FastAPI + Celery + PostgreSQL + Redis + ChromaDB + React + Ant Design + Docker Compose

- 仓库地址：[Kared331/SolidityGuard](https://github.com/Kared331/SolidityGuard)

### 2026-10-18 · 首次真实 LLM 运行（DeepSeek）

- **发现 100% 假阴性**：schema 要求 `impact`/`confidence` 必填，prompt 未要求 → 10/10 finding 被丢弃，报告显示 "completed, 0 findings"；账本的 `invalid_findings=10` 是唯一信号。
- **修复**：可选字段 + prompt 对齐 + 回归测试。
- **结果**：同一合约产出 9 条 finding，其中 `withdraw` 的 SWC-107 重入被 Critical 命中。
- **记录**：`docs/evidence/first-real-llm-run.md`。
### 2026-10-18 · 6A 覆盖可核算性实验

- **实验**：4 类故障（budget / rag_failure / llm_error / parse_error）× 100 次随机注入，全部被账本标记，Clopper–Pearson 95% 下界 **0.9705**。
- **单元守恒**：corpus 20 个合约，账本单元数 == 提取数，四项恒等式成立，失配 0。
- **口径**：证明的是"提取→入账不丢失"，不是 solc AST 交叉验证；模型质量另见 first-real-llm-run。
- **新增**：`docs/evidence/run_6a.py`（可重跑）与 `tests/test_coverage_accounting.py`（5 条回归）。
- **测试**：164 单测（+5）。
### 2026-10-18 · 6B 固定预算调度实验

- **语料**：143 个 SmartBugs-curated 已标注漏洞合约 + 133 个无已知漏洞的 DeFi/库合约（276）。
- **结果**：风险排序在 B≥50 时显著优于随机（p=0.040 @50，0.005 @100/150），B=100 时 recall 0.36→0.54；B=10/25 不显著（0.055/0.090）。
- **口径**：测的是"预算内触及的已知漏洞合约"，不是"检出"；因此不调用模型，结果确定可复现。
- **新增**：`docs/evidence/run_6b.py`、`fetch_benchmark.py`、`budget-scheduling.md`；解析器补上匿名 fallback（`function ()`）。
- **测试**：166 单测（+2）。
### 2026-10-18 · 增量审计地基（毕设选题 A）

- **新增** `services/incremental/`：unified diff 解析（多 hunk/纯删除/删除文件）+ 行区间到 `FunctionUnit` 的映射。
- **规则**：diff 未命中任何函数（import/状态变量）时回退整文件审计；跨文件影响明确标注为"未分析"。
- **基线**：160 个合成单函数改动，选择 160/160 正确，平均审计量减少 91.5%。
- **局限**：合成 diff、单函数改动；"少审"风险（改动 A 破坏 B）当前无法发现。
- **测试**：175 单测（+9）。
### 2026-10-18 · 增量审计全链路（选题 A）

- **新增** `POST /projects/{id}/incremental-audit`（接收 unified diff）与 `GET /runs/{a}/compare/{b}`。
- **增量调度**：diff → 函数级映射 → 只审变更函数；未触及函数记为 `unchanged/not_in_diff`，不调用模型。
- **账本**：新增 `functions_unchanged`（迁移 015），恒等式扩为五项；分母仍是真实函数数。
- **实测**（项目 #68）：8 函数 → 审 1 / 未变 7；对比 added=1 removed=19 persisted=2；报告含 Unchanged 行。
- **CI**：新增 `.github/workflows/solidguard-incremental.yml.example`（接口已验证，未在真实 runner 跑过）。
- **测试**：179 单测（+2）。
### 2026-10-18 · 增量审计 UI（审计运行 tab）

- **新增** `GET /api/v1/projects/{id}/runs` 与 `GET /api/v1/runs/{id}`（覆盖率分项 + 增量计划 + 逐函数账本）。
- **前端**：ProjectDetail 新增「审计运行」tab——运行列表、五段覆盖率条、增量计划（changed/unchanged）、逐函数账本、粘贴 diff 触发、两次运行对比 Drawer。
- **测试**：180 单测（+1）；`npm run build` 通过。
### 2026-10-18 · CI 触发模拟验证 + UI 收尾

- **CI 模拟**：真实 git 仓库 + 真实 `git diff`，插入一行导致行号下移，增量仍精确选中 `withdraw`（8 提取 / 1 审 / 7 未变，missing=[]）。
- **口径**：对比按 `(合约, 函数, 严重度)` 去重，运行 B 的 5 行 findings 合并为 3 个键。
- **UI**：默认进入「审计运行」tab；运行详情增加「生成报告」按钮。
- **未验证**：GitHub 托管 runner 的网络可达性（需 self-hosted），属部署配置而非代码。
