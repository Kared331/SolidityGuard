# 审计完整性 · 任务分解

> 配套设计：[`spec.md`](./spec.md)
> 原则：**每刀独立可回滚、先写失败测试、不混入无关改动**。四刀全部完成后才重新讨论"加功能"。

---

## 0. 执行纪律

1. 每刀一个 commit，message 带 `[integrity-N]` 前缀，便于单独回退；
2. 每刀先提交测试（红），再提交实现（绿），CI 上能看到"红→绿"；
3. 每刀结束跑全量单测：`venv\Scripts\python.exe -m pytest tests -m "not integration and not perf" -q`；
4. 不顺手重构、不顺手改前端、不顺手调参数；
5. 任何"顺带发现"的问题记入 `docs/design/audit-integrity/followups.md`，不在本批次处理。

---

## 刀 1 — 判定层：提取正确性（0.5 天，已完成）

**目标**：修掉 D2/D3/D4/D5 四个实测缺陷（见 [`docs/evidence/extraction-baseline.md`](../../evidence/extraction-baseline.md)），**不重写解析器、不动数据库、不动 severity**。

> D1（关键词过滤）按决策推迟；severity 与 `unknown` 出口一并推迟到刀 2——若此时单独删除"失败即 finding"，会出现"失败不可见"的中间态。

### 改动清单

| 文件 | 动作 |
|---|---|
| `backend/app/services/engine/solidity_units.py` | **新增**（约 190 行，含注释）：掩码注释/字符串 → 扫描 `function\|constructor\|receive\|fallback` → 遇 `;` 判声明 → 大括号配对 → `extract_functions()` + `select_units()` |
| `backend/app/services/engine/llm_audit.py` | `_extract_key_functions` 改为薄适配层，调用 `select_units(extract_functions())`，保留原 dict 形状 |
| `tests/test_solidity_units.py` | **新增** 7 条 |

### 测试（先红，每条对应一个实测缺陷）

| # | 用例 | 断言 | 缺陷 |
|---|---|---|---|
| 1 | 注释内 `function fake() { require(...) }` | 不产生单元 | D4 |
| 2 | 字符串 `require(ok, "}")` | body 完整（`require(more)` 仍在） | D5 |
| 3 | interface 声明 + 同文件实现 | 声明不产生单元，实现 body 完整 | D2 |
| 4 | `constructor` / `receive` / `fallback` | 均被提取且 kind 正确 | D3 |
| 5 | 选择策略 | 特殊函数恒入选；无关键词普通函数仍被跳过 | D1 推迟 |
| 6 | `VulnerableToken.sol` | 单元集合 == {constructor, transfer, withdraw, getBalance} | D3 |
| 7 | 嵌套 `for { if { } }` | body 完整、行号正确 | — |

### DoD（已验收）

- [x] 7 条测试全绿；
- [x] 现有 106 条单测不回归（113 passed）；
- [x] 重跑测量脚本：`extracted = 1896 = reference`、`missed = 0`、`noise = 0`、`body_mismatch = 0`，ctor/receive/fallback = 13/1/1；
- [x] `selected/ref = 78.8%`，D1 未修且已在证据文档中登记为已知缺口。

---

## 刀 2 — 账本：覆盖与降级可见（1.5 天，代码完成）

**目标**：两条恒等式成立并可被断言；报告数字与账本、数据库三者一致。
**详细设计**：[`blueprint.md` §P1](./blueprint.md)（本节只列改动面与验收，契约以蓝图为准）。

### 改动清单

| 文件 | 动作 |
|---|---|
| `backend/alembic/versions/013_add_audit_runs.py` | **新增**迁移：建 `audit_runs`、加 `llm_audit_results.audit_run_id`（nullable + FK + index） |
| `backend/app/models/audit.py` | **新增** `AuditRun`；`LLMAuditResult` 仅增 `audit_run_id`（不加 `provenance_json`） |
| `backend/app/services/engine/llm_audit.py` | `_audit_single_function` 返回 `(findings, status, reason)`；`_normalize_severity()`；删三处 `unknown` 出口与 injection-as-finding |
| `backend/app/services/engine/llm_audit.py` | **删除**死代码 `LLMAuditEngine.execute()`（无调用方、无测试） |
| `backend/app/services/engine/llm_audit.py` | RAG 批量/逐条失败计数（[L434-L457](../../../backend/app/services/engine/llm_audit.py#L434-L457)）；预算跳过计数（[L245-L247](../../../backend/app/services/engine/llm_audit.py#L245-L247)） |
| `backend/app/tasks/run_llm_audit.py` | 开始建 run（`running`）→ 汇总 per-file 结果 → 单 session 写 findings + UPDATE run；异常时标 `failed` 再 raise |
| `backend/app/tasks/cleanup.py` | 删除顺序加 `audit_runs`（在 `llm_audit_results` 之后），否则 FK 违约且静默失败 |
| `backend/app/services/chroma_client.py` | **删除**两处裸 `Exception` 重试谓词 |
| `backend/app/services/report_generator.py` | 增 `audit_coverage`；LLM findings 限定最新 run；`polish_with_llm` 用 `{**findings}` 保留第 4 个键 |
| `backend/app/services/templates/report.html.jinja2` | 新增覆盖段 + 降级横幅；DOCX 同步 |

### 测试（先红，12 条）

| # | 用例 | 断言 |
|---|---|---|
| 1 | 正常 | `completed`，audited = extracted |
| 2 | 预算耗尽 | skipped = extracted，reason=budget，`degraded` |
| 3 | LLM 抛异常 | failed = extracted，reason=llm_error |
| 4 | 响应不可解析 | failed，reason=parse_error |
| 5 | RAG 全失败 | audited 不变，`rag_failures = extracted`，`degraded` |
| 6 | 文件读不了 | `files_unreadable=1`，extracted=0 |
| 7 | 恒等式 | 任意构造结果下 F 与 U 同时成立（U 在 P5 扩为四项，含 `filtered`） |
| 8 | 最新 run | 两次审计后报告只含最新 findings |
| 9 | 旧数据 | `audit_run_id` 全 NULL 时报告仍含历史 findings |
| 10 | 报告渲染 | 覆盖率数字与账本一致；degraded 有横幅 |
| 11 | 清理 | 建 run + finding 后 cleanup 无 FK 报错 |
| 12 | 迁移 | upgrade / downgrade 各一次 |

`tests/test_audit_integrity.py::TestSeverity`（3 条，并入 12 条内计数）

| # | 用例 | 断言 |
|---|---|---|
| a | LLM 返回 `"high"` | 归一为 `"High"` 落库 |
| b | LLM 返回 `"UNKNOWN"` | 不落库，计入 `invalid_findings` |
| c | LLM 缺少 `severity` | 不落库，**不补 `unknown`** |

### DoD

- [x] 25 条测试全绿（6 注入 + 6 恒等式 + 5 报告 + 1 清理 + 1 迁移 + 3 引擎 + 3 severity），全量 138 passed；
- [x] 迁移 upgrade / downgrade 离线 SQL 均生成成功；
- [x] `ruff check backend` / `format --check backend` 通过；
- [ ] 报告数字 = 账本 = 数据库（P2 E2E 已验证：项目 #47，见 `docs/evidence/e2e-run.md`）；
- [ ] cleanup 在含新表的数据上真实执行（仅单测覆盖顺序，未做真实执行）；
- [ ] ISS-01/02 状态更新为"已修复（有测试）"——已更新 PRR，待 P3/P4 后复核。

---

## 刀 3 — SWC 快照化（0.5–1 天，✅ 已完成 2026-10-18）

**目标**：知识库离线可复现、有版本、可回归。

### 改动清单

| 文件 | 动作 |
|---|---|
| `backend/app/services/engine/data/swc_registry.json` | **新增**离线快照（37 条，88 KB） |
| `backend/app/services/engine/swc_sync.py` | 默认读快照；`refresh=true` 才联网；schema + 条目数校验；`kb_version()` = 条目集 hash |
| `backend/app/tasks/sync_swc.py` | 按 `swc_id` 幂等 upsert；Chroma 写入 **metadatas**（修复 title 恒为 Unknown） |
| `backend/app/tasks/run_llm_audit.py` | `audit_runs.kb_version` 落库 |
| `backend/app/api/knowledge.py` / `knowledge_service.py` | `?refresh=true` 才联网，默认快照 |
| `backend/app/services/templates/report.html.jinja2` | 覆盖率段显示 model / prompt / KB 版本 |

### 测试

`tests/test_swc_snapshot.py`（11 条）

| 组 | 断言 |
|---|---|
| 加载与校验 | 37 条、id 唯一、字段非空；条数/字段不符抛错 |
| 版本 | 稳定；条目改动后变化 |
| 离线 | 默认路径下 `httpx.get` 抛异常也不会被调用 |
| 刷新 | `refresh=True` 用拉取结果，`source=refresh` |
| Chroma | metadata 全为字符串、无 None；文档含 title |
| 幂等 | 新条目 `add`、已有条目只更新不新增 |

### DoD

- [x] 断网可同步（快照路径生效）；
- [x] 报告页脚显示 `kb_version`（实测 `swc-52c82b8a`）；
- [x] 重复同步幂等（`vulnerability_entries` 仍 37 行）；
- [x] Chroma metadata 修复（title 不再是 `Unknown`）；
- [ ] 检索 golden 测试：**未落地为 pytest**（依赖本地模型与 Chroma 状态，易变环境测试），改为可重跑探针 + 证据表；实测 top-1 4/10。

---

## 刀 4 — Fuzzer 判定（1.5–2 天，✅ 已完成 2026-10-18，范围收窄）

**目标**：`forge test` 能真实发现不一致，而不是恒真断言。

### 改动清单

| 文件 | 动作 |
|---|---|
| `backend/app/services/engine/fuzzer.py` | 解析函数签名（参数类型列表），按签名生成调用；构造函数按签名生成参数 |
| `backend/app/services/engine/fuzzer.py` | 弃用 `try/catch` 空转与 `assertEq(x,x)`；改为**ERC-20 供给守恒**不变量（唯一实现的不变量） |
| `backend/app/services/engine/fuzzer.py` | fuzz 目标优先取 Slither/LLM 已标记的高危函数 —— **未做**（见下） |
| `backend/app/tasks/run_fuzzer.py` | 日志带 `status`（ok / compile_error / no_invariant_derivable / timeout / forge_missing） |
| `backend/app/services/report_generator.py` | fuzz finding 标题改为 `Contract.function (risk_type)` |

### 测试

| 用例 | 断言 |
|---|---|
| 生成代码对 `VulnerableToken.sol` | `forge build` 通过（容器内实跑） |
| 守恒不变量 | 触发失败并产出 counterexample（实测 `args=[1797, 3557]`） |
| 带参构造函数 | 生成 `new VulnerableToken(uint256(1))` |
| 生成代码语法 | 不出现 `func(x)` 这类签名不匹配调用；不出现 `assertEq(x, x)` |
| 不可推导时 | `no_invariant_derivable`，不写测试文件 |

### DoD

- [x] `forge test` 在 fixture 上产出至少一条真实失败；
- [x] `raw_output` 截断到 64KB；
- [x] fuzz 在临时工作目录执行，不污染上传目录（`uploads/47` 实测前后一致）；
- [x] 失败带 `contract` / `function` / `risk_type` 落库；
- [ ] **重入检测**：未实现，通用 fuzzer 无法凭空构造攻击者合约；已在 README 与证据文档中划清范围；
- [ ] 高危函数优先取 Slither/LLM 结果：未做，等 P5 后按需要再加。

> 环境：宿主无 Foundry，真实运行在 worker 容器（`forge 1.7.1`）完成；单测覆盖生成器逻辑，不依赖 forge。

---

## 5. 验收命令与证据

```powershell
# 单测（每刀结束都要跑）
venv\Scripts\python.exe -m pytest tests -m "not integration and not perf" -q

# 集成（需 docker compose up -d）
venv\Scripts\python.exe -m pytest tests -m integration -q

# 检索 golden（需本地 embedding 模型）
venv\Scripts\python.exe -m pytest tests/rag -m rag -q
```

**最终证据**（写入 `docs/evidence/audit-integrity.md`）：

1. 改造前/后同一 fixture 的提取数、送审数、finding 数对照表；
2. 报告截图或 HTML 片段（覆盖率段 + 降级横幅）；
3. 三条不变量的测试名称与运行输出；
4. `audit_runs` 一条真实记录（JSON 导出）。

---

## 6. 排期

| 刀 | 内容 | 预估 | 依赖 |
|---|---|---|---|
| 1 | 判定层 + 契约 | 1 天 | 无 |
| 2 | 账本 + 输出 | 1 天 | 刀 1 |
| 3 | SWC 快照 | 0.5–1 天 | 无（可与刀 2 并行） |
| 4 | Fuzzer | 1.5–2 天 | 刀 2（复用 audit_run 链接） |

合计约 **4–5 个工作日**。刀 3 可并行，关键路径是 1 → 2 → 4。
