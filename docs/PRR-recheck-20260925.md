# SolidGuard 复检就绪度报告（PRR Recheck）

> **日期**：2026-09-25
> **性质**：实施后复检（对照 2026-08-28 首轮 PRR「有条件达标」的解除条件）
> **依据**：`MODIFICATION_BLUEPRINT.md` v1.1（28 项修改）+ v3.0.1 增量 + 2026-09-16 ISS 诊断
> **方法**：实测取证（服务栈运行态 + 三套测试 + 代码级抽查 + 端到端链路）
> **状态**：本地内部文档，未入库

---

## 一、裁定结论

**有条件达标（Conditional Go）——工程基建已达标，审计能力可信度存在结构性缺口。**

| 层面 | 裁定 | 一句话依据 |
|------|------|-----------|
| 工程基建（P0-P2 蓝图交付） | ✅ **Go** | 28 项修改全部落地并经本次实测验收，三套测试 122/122 全绿 |
| 端到端链路 | ✅ **Go** | 上传→分析→审计→报告→下载→SSE 全链路真实走通（项目 #32） |
| 审计能力可信度 | ⚠️ **Conditional** | ISS-07 Fuzzer 假阴性 100%、ISS-01/02/08 静默降级不可观测（2026-09-16 诊断，未修复） |

**与首轮 PRR 的差异**：首轮（2026-08-28）的条件项为工程基建（P0-P2 共 28 项）——本次全部验收通过；新条件转移至**审计能力可信度**（ISS 系列 12 项，其中 4 项高危）。

---

## 二、本次复检证据清单（全部为 2026-09-25 实测）

### 2.1 运行环境

| 项 | 结果 |
|----|------|
| Docker 服务栈 | 5 容器 Up（api/frontend/worker/postgres/redis），postgres/redis healthy |
| `/health` | `{"status":"ok","checks":{"postgres":"ok","redis":"ok"}}` |
| 前端入口 | `http://127.0.0.1:3000/` HTTP 200，`lang="zh-CN"` |
| API 文档 | `http://127.0.0.1:8000/docs` HTTP 200 |
| 环境漂移 | 已消除：本地 venv Python 3.11.9 == 容器 3.11（原 3.9.13 记录已过时） |

### 2.2 测试套件（三套全绿）

| 套件 | 结果 | 耗时 | 说明 |
|------|------|------|------|
| 单元测试（默认） | **95/95 passed** | 18.13s | marker 排除 integration/perf |
| 集成测试（`-m integration`） | **20/20 passed** | 44.86s | **真实执行非 SKIP**（P0-1 激活后首次在服务栈上全量跑通） |
| 性能压测（`-m perf`） | **7/7 passed** | 3.61s | 引擎级基线保持 |
| 前端构建 | `tsc && vite build` 通过 | 1.95s | 主 bundle gzip 65.67KB |

### 2.3 端到端链路（项目 #32，fixtures/test_contracts.zip）

| 步骤 | 结果 | 证据 |
|------|------|------|
| 1. 上传 | ✅ | `POST /api/v1/projects` → id=32, status=uploaded |
| 2. Slither 分析 | ✅ | 任务 SUCCESS；真实检出 tautology（含源码定位 `VulnerableToken.sol#15-20`） |
| 3. LLM 审计 | ✅（降级路径） | 任务 SUCCESS；6 条结果，失败文案可区分（`LLM audit failed (Illegal header value b'Bearer ')`——空 key 预期行为，S4 可观测性生效） |
| 4. 报告生成 | ✅ | `reports/32/report.html`，15.7KB（B3 Slither elements 数组解析修复在真实数据上验证） |
| 5. 报告下载 | ✅ | HTTP 200, 15723 bytes |
| 6. SSE 事件流 | ✅ | 连接建立即收 `snapshot`（detections:1/audit:6/reports:1）；审计完成即收 `new_audit_results (count=6)`——f7f99f2 发布端接线生效 |

---

## 三、蓝图 P0-P2 验收对照（28 项 → 全部通过）

### P0 阻塞修复（6/6 ✅）

| 编号 | 项 | 验收证据（本次代码级抽查） |
|------|-----|---------------------------|
| P0-1 | 集成测试激活 | 20/20 真实执行通过（非 SKIP） |
| P0-2 | Provider 重试 | `base.py:16` 白名单 `{429,500,502,503,504}` 重试；401/403 立即失败；tenacity stop=3, 指数退避 2-30s |
| P0-3 | LLM 独立限流 | `sync_wrapper.py:38` 双重检查锁 + mtime 热加载；`with _get_semaphore()` 包裹协程提交 |
| P0-4 | 事件循环复用 | 常驻守护线程循环，懒初始化（Celery prefork fork 安全），`run_coroutine_threadsafe` |
| P0-5 | 失败态干净回传 | `run_llm_audit.py:191-194` 直接 raise，FAILURE 交 Celery 原生标记 |
| P0-6 | report_generator 回归 | test_report_generator.py 在 95 单测内通过；真实链路 B3 验证 |

### P1 达标差距项（11/11 ✅）

| 编号 | 项 | 验收证据 |
|------|-----|---------|
| P1-1 | 任务幂等 | `task_dispatcher.py:88` `_has_active_task` 拦截重复派发，抛 `TaskAlreadyRunning`（声明局限：仅查 active，单 worker 场景） |
| P1-2 | Error Boundary | `main.tsx:51` 包裹应用根 |
| P1-3 | axios 拦截器 | `client.ts:14` `interceptors.response.use` |
| P1-4 | Provider 统一关闭 | `celery_app.py:66` worker_process_shutdown 钩子（与 FastAPI 侧对称） |
| P1-5 | Compose 加固 | restart policy + env_file（服务栈实测自愈正常） |
| P1-6 | 配置单一事实来源 | alembic env.py 回退 settings.DATABASE_URL（迁移在容器启动中正常执行） |
| P1-7 | Token 预算持久化 | `token_budget.py:66-117` Redis 30 天 TTL + max 合并防回退；`run_llm_audit.py:50,187` load/persist 接线 |
| P1-8 | SSE 断线恢复 | `useSSE.ts:151-163` onerror 不再 close()；15s 后降级轮询；本次实测事件流正常 |
| P1-9 | 优雅关闭超时 | `celery_app.py:44` 可配置，默认 300s |
| P1-10 | Schema 校验接入 | `llm_audit.py:364-377` `AuditFindingSchema(**finding)` 拒绝非法条目并告警 |
| P1-11 | README 真实化 | 95/20/7 三套测试数与本次实测一致 |

### P2 打磨项（8/8 ✅）

| 编号 | 项 | 验收证据 |
|------|-----|---------|
| P2-1 | 指标加锁 | provider_stats 计数线程安全（llm_retry 的 before_sleep 引用） |
| P2-2 | 线程池-信号量边界 | embedding 只锁网络 I/O（蓝图验收 + 95 单测含覆盖） |
| P2-3 | 长任务进度 | useTaskProgress 派生 hook（避免重复 SSE 连接） |
| P2-4 | lifespan 迁移 | asynccontextmanager |
| P2-5 | 上传预校验 | `UploadPage.tsx:31-36` 50MB 与 nginx client_max_body_size 对齐 |
| P2-6 | doctor 自检 | manage.ps1 子命令 |
| P2-7 | 前端速赢包 | `lang="zh-CN"`（页面实测）+ Toast 体系 |
| P2-8 | 解压安全固化 | 4 项 tar 安全回归测试在 95 单测内；upload.py zip/tar 双分支防护在位 |

### v3.0.1 增量（已验收 ✅）

- **知识库同步 500 修复**：`_apply_with_connection` 显式连接发布（`task_dispatcher.py:71`）；`test_trigger_knowledge_sync` 集成实测通过
- **SWC 每周自动同步**：beat `sync-swc-weekly`（周一 03:10 UTC）
- **SSE 发布端接线**（f7f99f2）：snapshot + worker 完成事件——本次 E2E 实测收到两种事件

---

## 四、遗留风险登记册（新条件项：ISS 系列，2026-09-16 诊断，2026-10-18 部分修复）

> 性质：**审计能力可信度**缺口，非工程基建缺陷。诊断文档：`docs/SolidityGuard-issues-diagnosis-20260916.md`

| 编号 | 风险 | 严重度 | 本次验证状态 | 建议处置 |
|------|------|--------|--------------|----------|
| ISS-07 | Fuzzer 生成测试失能（编译失败/恒真断言 `assertEq(x,x)`），假阴性 100% | 🔴 高 | **确认未修**：`fuzzer.py:100,161` 恒真断言仍在 | **P5-1 首修**：按真实签名生成调用 + 不变量断言 |
| ISS-01 | Token 预算不足静默丢函数，用户看到"0 漏洞"无从分辨 | 🔴 高 | **已修（2026-10-18）**：单元状态 `skipped/budget` 入账本，报告显示覆盖率；待 E2E 验收 | — |
| ISS-08 | Slither solc 回退对跨文件 import 项目静默全空 | 🔴 高 | 未复测（诊断可信） | P2 待办：degraded 标记 + 失败文件清单 |
| ISS-02 | RAG 大面积失败静默降级为裸 LLM | 🔴 高 | **已修（2026-10-18）**：`rag_failures` 计数 + `degraded` 状态；待 E2E 验收 | — |
| ISS-03 | 函数提取正则漏检（recall 结构性上限） | 🟡 中 | **已修（2026-10-18）**：`solidity_units.py` 取代正则+关键词；实测 1896=1896，漏/噪 0；见 `tests/test_solidity_units.py` | — |
| ISS-04 | 读文件无大小上限（先全量读入再截断） | 🟡 中 | **确认未修**：无 getsize 校验 | P5-6：前置大小检查（1MB 阈值） |
| ISS-05 | 双轨架构（同步引擎 + 闲置异步 pipeline） | 🟡 中 | 架构债不变 | ISS-01/02/07/08 修复后再收敛 |
| ISS-06 | 测试偏 mock，未证明审计能力 | 🟡 中 | 属实（95 单测以 mock 为主） | P1 真实能力基准（fixture 已具备起步条件） |
| ISS-09~12 | raw_result 口径/目录污染/输出上限/结果映射 | 🟡 中 | 未复测 | 随 ISS-07 一并处理 |

**风险接受声明**：当前无真实 LLM_API_KEY，LLM 审计走降级路径——降级文案可观测（S4 已达标），但**真实模型审计能力未验证**（同首轮 F3，条件不变）。

---

## 五、就绪度矩阵

| 维度 | 状态 | 关键证据 | 缺口 |
|------|------|----------|------|
| 可靠性（LLM 自愈/任务生命周期） | 🟢 达标 | P0-2/3/4/5 + P1-1/7/9 全验收 | — |
| 可观测性 | 🟢 达标 | /health 双检查、S4 失败原因、SSE snapshot+事件、provider_stats | ISS-01/02 降级不可见（属能力维度） |
| 安全 | 🟢 达标 | Zip/Tar Slip 防护、Prompt 注入消毒、API Key fail-closed、非 root 容器 | — |
| 变更安全（测试/CI） | 🟢 达标 | 122/122 三套全绿、CI（ruff 达标）、前端 tsc 构建通过 | ISS-06：mock 密度高 |
| 容量与性能 | 🟢 达标 | P4 数据：文件级并行 5.22x、函数级 3.79x、embedding 批量 12x+ | — |
| 运维 | 🟢 达标 | 容器自愈、doctor 自检、TROUBLESHOOTING、优雅关闭 300s | — |
| **审计能力可信度** | 🔴 **不达标** | Slither 真实检出 ✓；**Fuzzer 假阴性 100%、静默降级 3 处** | ISS-01/02/07/08 |

---

## 六、完成定义（DoD）与后续路径

**解除「审计能力可信度」条件的 DoD**（建议作为 Phase 5 蓝图输入）：

1. ISS-07 修复后：fuzz 对 `VulnerableToken.sol` 能产出真实失败信号（SWC-107 重入可触发）
2. ISS-01/02/08 修复后：预算/RAG/solc 三类降级在结果中可见（degraded/skipped 字段 + 前端提示）
3. 配置真实 LLM_API_KEY 后跑一次真实能力基准（fixture：VulnerableToken 2 漏洞 / SimpleToken 安全基线）

**优先级排序**（沿诊断文档建议）：ISS-07 → ISS-01 → ISS-08 → ISS-02 → ISS-10/11/12 → ISS-09 → ISS-05（最后收敛）→ P1 基准（可并行）。

---

## 七、本次复检工作区状态备注

- 工作区干净（HEAD=f7f99f2），仅 2 个未跟踪诊断文档（`docs/*-20260916.md`，其一为 0 字节空文件，建议清理）
- E2E 产生的项目 #32 数据留存于运行栈中（不影响后续操作，可经 cleanup 任务清理）

---

*本报告为复检实测产物。裁定遵循：无证据不宣称、有缺口必登记。*
