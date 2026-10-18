# 审计完整性总蓝图

> 日期：2026-10-18
> 性质：可执行计划，不是愿景文档
> 配套：[`spec.md`](./spec.md)（契约）、[`tasks.md`](./tasks.md)（分解）、[`evidence/extraction-baseline.md`](../../evidence/extraction-baseline.md)（实测基线）
> 版本：v1.0

---

## 0. 一页结论

本项目目前有 **22 个已知问题**，其中 4 个已修、18 个未修或推迟；有 **1 个根本问题**（没有可验证的主张），它不在这 22 个里，也无法靠修这 22 个自动解决。

总蓝图分 7 个阶段。前 6 个阶段的唯一目的，是让第 7 阶段（研究命题）**具备被测量和被证伪的资格**；不是为了让系统"更完备"。

**现在处在 P5 结束**：提取（P0）、账本（P1）、主链路验证（P2）、Fuzzer（P3，范围收窄）、知识库（P4）、D1 决策（P5）均已完成，证据见 `docs/evidence/`。**只剩 P6（研究命题），需要真实 LLM key。**

---

## 1. 问题总表

状态：`已修` / `未修` / `未验证` / `推迟`

| # | 问题 | 证据 | 状态 | 阶段 |
|---|---|---|---|---|
| **R1** | 无可证伪主张、无基准、无真实 LLM 运行 | 全文 | 未修 | P6 |
| **D1** | 关键词过滤丢弃 21.7% 函数（P5 实测 20.9%） | [evidence/p5-corpus](../../evidence/p5-corpus.md) | **已修（P5）：保留过滤，但过滤项入账本** | P5 |
| **D2** | interface 声明吞 `{`，22 个幻影单元 | 同上 §4 | 已修 | P0 |
| **D3** | ctor/receive/fallback 15 个从未提取 | 同上 §4 | 已修 | P0 |
| **D4** | 注释里的 `function` 被当真函数 | 同上 §4 | 已修 | P0 |
| **D5** | 字符串 `}` 截断 body | 同上 §4 | 已修 | P0 |
| **D6** | 覆盖率不可见（实际只审 58.2% 字节） | 同上 §3 | 未修 | P1 |
| **O1** | `severity="unknown"` 把故障混入 findings | [L339](../../../backend/app/services/engine/llm_audit.py#L339)/[L357](../../../backend/app/services/engine/llm_audit.py#L357)/[L383](../../../backend/app/services/engine/llm_audit.py#L383) | 未修 | P1 |
| **O2** | 预算耗尽静默丢函数 | [L297](../../../backend/app/services/engine/llm_audit.py#L297) | 未修 | P1 |
| **O3** | RAG 失败静默退化为裸 LLM | [L505](../../../backend/app/services/engine/llm_audit.py#L505) | 未修 | P1 |
| **O4** | solc 回退对跨文件项目静默全空 | `slither.py` | 未修 | P2（与账本不同表，避免混任务） |
| **C1** | Chroma 重试谓词退化为裸 `Exception` | `chroma_client.py` | 未修 | P1 |
| **O6** | 重复审计导致 finding 在报告里重复计入 | [report_generator.py:89](../../../backend/app/services/report_generator.py#L89) | 未修 | P1 |
| **E1** | Fuzzer 恒真断言，假阴性 100% | [fuzzer.py](../../../backend/app/services/engine/fuzzer.py) | 已修（P3，范围收窄） | P3 |
| **E2** | `forge init --force` 污染上传目录 | ISS-10 | 已修（P3） | P3 |
| **E3** | `-vvv` 输出无上限入库 | ISS-11 | 已修（P3） | P3 |
| **E4** | fuzz 失败无法映射到合约/风险类型 | ISS-12 | 已修（P3） | P3 |
| **K1** | SWC 运行时联网拉取、无版本 | `swc_sync.py` | 未修 | P4 |
| **K2** | 检索无回归基线 | 无 | 未修 | P4 |
| **V1** | 集成 / E2E / 性能测试未在改动后运行 | docker 未启动 | 未验证 | P2 |
| **M1** | README `210s → 70s` 无出处 | [README L27](../../../README.md#L27) | 未修 | P2 |
| **M2** | PRR 复检状态过期（ISS-03 仍写未复测） | [PRR L119](../../PRR-recheck-20260925.md#L119) | 未修 | P2 |
| **M3** | 三份诊断文档未纳入版本控制 | `git status` | 未修 | P2 |

---

## 2. 编写原则：反防御性

这七条是硬规则，违反即打回。每条都附本项目里的真实反例。

| # | 规则 | 本项目的反例 |
|---|---|---|
| 1 | **无观测不做**：改动必须链接一条证据（数字、用例、日志），否则只进 backlog 不排期 | 初稿要求"重写词法分析器"，实测边界准确率 99.2%，纯属臆想 |
| 2 | **无红测试不写实现**：先提交会失败的测试，再做实现 | P0 的 7 条测试全部先红 |
| 3 | **按唯一调用方设计**：不预留"以后可能用到"的参数、抽象层、接口 | `provenance_json` 是既有列的重复，已删 |
| 4 | **失败显式化**：不吞异常、不补默认值、不静默降级 | `severity="unknown"`、`rag_contexts[i]="None found"` |
| 5 | **删除优先**：能删 10 行就不加 10 行 | `_extract_key_functions` 68 行 → 14 行适配层 |
| 6 | **测试必须能失败**：删掉实现后测试应变红，否则是装饰 | 若测试只断言"函数被调用过"，它永远绿 |
| 7 | **度量先于声明**：没有基线数字，不写性能/质量结论 | README 的 67% 降幅没有任何测量出处 |

**判据**：如果一段代码删掉后没有任何测试变红、没有任何观测指标变化，它就是防御性代码。

---

## 3. 阶段蓝图

```
P0 提取正确性 ✅
   └─→ P1 账本与可见性 ──→ P2 主链路验证 ──┬─→ P3 Fuzzer
                                          ├─→ P4 知识库
                                          └─→ P5 D1 决策
                                                    └─→ P6 研究命题
```

### P0 — 提取正确性（已完成）

| 项 | 内容 |
|---|---|
| 改动 | 新增 `solidity_units.py`；`_extract_key_functions` 缩为适配层 |
| 验收 | `extracted = 1896 = reference`，missed/noise/body_mismatch 全 0；ctor 13 / receive 1 / fallback 1 |
| 证据 | 113 单测通过；[evidence §6](../../evidence/extraction-baseline.md) |
| 遗留 | D1 未修（78.8% 选中率），D6 未修 |

---

### P1 — 账本与可见性（1.5 天，**代码完成，待 P2 验收**）

**这一步要证明的一句话**：一次审计结束后，"审了哪些函数、每个的结局、为什么"能从数据库一行记录里复现，并与报告上的每个数字对得上。

#### P1.0 三个代码事实（先纠正初稿的错误假设）

1. `LLMAuditEngine.execute()`（项目级入口）**没有任何调用方**——生产路径 `run_llm_audit` 直接调 `execute_single_file`。初稿写的"`execute()` 返回 coverage"是错的：汇总必须在任务层做，而 `execute()` 应当**直接删掉**，否则要维护两套汇总逻辑。
2. `execute_single_file` 在 5 线程池里并行执行。账本**不需要锁**：每个线程返回自己的单元列表，任务层在 `as_completed` 之后串行合并。
3. `aggregate_findings` 查的是**全部历史** `LLMAuditResult`（[report_generator.py:89](../../../backend/app/services/report_generator.py#L89)）。同一项目跑两次审计，同一漏洞在报告里出现两次——这是已存在的 bug，P1 用 `audit_run_id` 顺手修掉（O6）。

#### P1.1 两条恒等式，不是一条

```
F:  files_total        = files_processed + files_unreadable
U:  functions_extracted = audited + skipped + failed + filtered   （仅统计 processed 文件）

> `filtered` 是 P5 加入的：关键词过滤掉的函数也要入账，否则分母会从 1759 缩到 1391，报告显示"100% 覆盖"。
```

只保留 U 会被"读不到文件 → 计 0 个函数"平凡满足。F 就是防这一手的。两条都要在测试里断言。

#### P1.2 单元状态机

| status | reason | 触发点 | 产 finding |
|---|---|---|---|
| `audited` | — | 响应可解析（含 `[]`，即无发现） | 是 |
| `skipped` | `budget` | `check_budget` 返回 False | 否 |
| `failed` | `llm_error` | `chat_completion` 抛异常 | 否 |
| `failed` | `parse_error` | `_parse_llm_json` 返回 None | 否 |
| — | `read_error` | 文件读不了（**文件级**，不产生单元） | 否 |

关键定义：`audited` 只表示"拿到可解析响应"，**不表示"审出了东西"**。空数组是正常结果。

#### P1.3 写入时序（两次 commit，故意不合并）

1. 任务开始 → `INSERT audit_runs(status='running')` → commit。崩溃时留下 `running` 残行，`doctor` 可检出。
2. 线程池跑完 → 合并 per-file 结果（纯数据，无共享可变状态）。
3. 单 session：批量写 findings（带 `audit_run_id`）+ UPDATE run 的计数/状态/`finished_at` → 一次 commit。
4. 任意异常 → UPDATE `status='failed'` 并 commit，然后 `raise`（不吞、不改 Celery 结果协议）。

#### P1.4 失败矩阵（6 条注入，逐条一个测试）

| 注入 | files | extracted | audited | skipped | failed | run.status |
|---|---|---|---|---|---|---|
| 正常 | n | m | m | 0 | 0 | completed |
| 预算耗尽 | n | m | 0 | m | 0 | degraded |
| LLM 异常 | n | m | 0 | 0 | m | degraded |
| 响应不可解析 | n | m | 0 | 0 | m | degraded |
| RAG 全失败 | n | m | m | 0 | 0 | degraded（`rag_failures=m`） |
| 文件读不了 | n | 0 | 0 | 0 | 0 | degraded（`files_unreadable=1`） |

#### P1.5 删除清单（比新增更重要）

| 删除 | 原因 |
|---|---|
| `LLMAuditEngine.execute()` | 死代码，无调用方、无测试 |
| 三处 `severity="unknown"` 出口 | 把基础设施故障伪装成审计结论 |
| injection warning 作为 finding | 它是输入安全告警，不是审计结论；移入 `details_json.warnings`，报告单独呈现 |
| `chroma_client` 两处裸 `Exception` 重试 | 会把 `TypeError` 这类代码 bug 重试 3 次再吞掉 |
| `severity` 的 DB `CHECK` 约束 | 应用层归一 + 测试足够，迁移越少越好 |

#### P1.6 报告

- `aggregate_findings` 增第 4 个键 `audit_coverage`；
- LLM findings 限定为**最新一次 run**（`ORDER BY id DESC LIMIT 1`）；无 run 时回退旧行为，旧数据必须有测试；
- `polish_with_llm` 首行改为 `polished = {**findings}`，否则第 4 个键会被它丢掉（[L149-L151](../../../backend/app/services/report_generator.py#L149-L151)）；
- 模板新增段：提取 / 已审 / 跳过 / 失败四列 + 原因分布 + 覆盖率 + 模型/提示词/知识库版本；
- `degraded` 时报告顶部横幅。

#### P1.7 迁移 013

按 spec §4.2 建 `audit_runs`、给 `llm_audit_results` 加 `audit_run_id`（nullable + FK + index）；`details_json` 用 `sa.JSON`；`downgrade` 反向删除。只加不删，旧数据 `audit_run_id=NULL`。

#### P1.8 清理任务

`cleanup.py` 是显式逐表删除（[L80-L90](../../../backend/app/tasks/cleanup.py#L80-L90)），新增表必须同步加一行，顺序为 `llm_audit_results` → `audit_runs`（FK 方向）。漏了会让清理任务撞 FK 约束失败——而它 `except Exception` 只记日志，等于"清理静默失效"。

#### P1.9 测试清单（12 条）

| # | 用例 | 断言 |
|---|---|---|
| 1–6 | P1.4 的六类注入 | 表中每一列 |
| 7 | 恒等式 | 对任意构造结果，F 与 U 同时成立 |
| 8 | 最新 run 过滤 | 两次审计后报告只含最新一次的 findings |
| 9 | 旧数据回退 | `audit_run_id` 全 NULL 时，报告仍包含历史 findings |
| 10 | 报告渲染 | 含覆盖率段；数字与账本一致；degraded 有横幅 |
| 11 | 清理顺序 | 建 run + finding 后执行 cleanup，无 FK 报错 |
| 12 | 迁移 | `upgrade head` / `downgrade -1` 各一次，列与表存在性正确 |

#### P1.10 出口判据

- 12 条测试全绿，且每条在实现回退时都能变红；
- 用 `VulnerableToken.sol` 跑一次（LLM mock），报告数字 = 账本 = 数据库；
- P2 的 E2E 通过。

#### P1.11 工期拆解

| 子项 | 工时 |
|---|---|
| 迁移 013 + 模型 | 0.25 d |
| 引擎返回 `(findings, status, reason)` + 删 unknown/死代码 | 0.5 d |
| 任务层汇总 + 写账本 | 0.25 d |
| 报告 + 模板 + DOCX | 0.25 d |
| cleanup + 12 条测试 | 0.25 d |
| **合计** | **1.5 d** |

比初稿多 0.5 天，多出来的是初稿漏掉的两件事：删死代码、修"重复计入"。

**实施结果**：25 条测试全绿，138 条单测通过，迁移 upgrade/downgrade 离线 SQL 均成功生成。实施期发现的三个问题（ABC 强制 `execute`、校验顺序让归一化失效、恒等式抓到错误测试）记录在 [`evidence/coverage-ledger.md`](../../evidence/coverage-ledger.md)。**未验证**：真实 Postgres 迁移、集成测试、E2E——这些是 P2 的出口判据。

> **P1 是整条路线的枢纽**：它之前，所有降级都是静默的；它之后，每一次跳过都能被指出来。路线 A 的全部素材在这一阶段产生。

---

### P2 — 主链路验证（0.5 天，✅ 已完成 2026-10-18）

**目标**：证明 P0/P1 没把生产链路搞坏。

| 步骤 | 命令 | 通过判据 |
|---|---|---|
| 起服务栈 | `docker compose up -d` | 5 容器 Up，`/health` 双 ok |
| 单测 | `pytest -m "not integration and not perf"` | ≥ 113 passed |
| 集成 | `pytest -m integration` | 20 passed（非 SKIP） |
| 性能 | `pytest tests/perf -m perf` | 7 passed |
| E2E | 上传 `test_contracts.zip` → 分析 → 审计 → 报告 | 报告含覆盖率段；恒等式成立 |

**同时清理对外材料**（都是 5 分钟的活，但拖久了就是债）：

- README L27 改为"基于 50ms mock 的编排开销推算"，或直接删除；
- PRR 的 ISS-03 改为"已修（见 `tests/test_solidity_units.py`）"；
- 三份诊断文档 `git add` 入库；
- CHANGELOG 增加本批次条目。

**出口**：全部通过才进 P3。任一失败 → 回滚 P0/P1 的最后一个 commit，先修再继续。

**实测结果**（证据：[`evidence/e2e-run.md`](../../evidence/e2e-run.md)）：迁移 012→013 在真实 Postgres 上执行成功；138 单测 / 20 集成 / 7 性能全绿；E2E 项目 #47 产出账本行 `4 = 0 + 0 + 4`、`1 = 1 + 0`，报告含覆盖率段与降级横幅。冷启动首轮集成有 2 个轮询超时 SKIP，栈热后复跑 20/20 通过（54.79s），判定为预热排队而非缺陷。

---

### P3 — Fuzzer 真实性（1.5–2 天，✅ 已完成 2026-10-18，范围收窄）

**目标**：让第三阶段真的能发现东西，或诚实地承认它不能。

| 项 | 内容 |
|---|---|
| 改动 | 按真实函数签名生成调用；构造函数带参；用不变量断言替代 `try/catch` 空转；`raw_output` 截断 64KB；`forge` 在临时目录执行 |
| 测试 | fixture 上 `forge build` 通过；重入不变量能触发失败并给出 counterexample；上传目录前后哈希一致 |
| 验收 | ~~`VulnerableToken.withdraw` 的 SWC-107 能被 fuzz 真实触发~~ |
| 若失败 | 如果 2 天内无法触发，**直接把 fuzzer 从"三阶段"降级为"可选实验功能"**，并在 README 里写明。这比留一个假阴性 100% 的引擎诚实 |

**实测结果**（证据：[`evidence/fuzz-baseline.md`](../../evidence/fuzz-baseline.md)）：

- 改造前：生成测试**编译失败**（无 import、无构造参数、签名不符），而 `failures=None` → 对外呈现"0 漏洞"；同时 `forge init --force` 污染了 `uploads/47`。
- 改造后：`VulnerableToken` 产出**真实失败**——`assertion failed: 0 != 1`，counterexample `args=[1797, 3557]`，映射到 `withdraw / supply_conservation`；`SimpleToken` 返回 `no_invariant_derivable` 而不是生成恒真测试；`uploads/47` 前后无新增文件。
- **范围收窄**：只实现了 ERC-20 供给守恒探针。**重入没有做到，也不应声称做到**——通用 fuzzer 无法凭空构造攻击者合约。原验收项（SWC-107）据此划掉，而不是含糊过去。
- 全量测试 145 passed（+7 条 fuzzer 单测）。

---

### P4 — 知识库可复现（0.5 天，✅ 已完成 2026-10-18）

| 项 | 内容 |
|---|---|
| 改动 | 37 条离线快照入库；默认读快照，`refresh=true` 才联网；`kb_version = swc-<hash8>`；按 `swc_id` 幂等 upsert |
| 测试 | 断网可同步；条目数 = 37；重复同步幂等；检索基线用探针记录 |
| 验收 | 报告页脚显示 `kb_version`；检索用探针记录 top-1/top-3（见证据） |
| 不做 | 不扩库、不调 topK、不比较模型——37 条通用描述不可能显著提升检出率，本阶段不做任何效果声明 |

**实测结果**（证据：[`evidence/kb-snapshot.md`](../../evidence/kb-snapshot.md)）：

- 快照 37 条随代码入库；默认路径实测**不联网**；`kb_version = swc-52c82b8a` 已写入 `audit_runs`；重复同步后 `vulnerability_entries` 仍 37 行。
- 探针发现一个静默缺陷：Chroma 从未写入 metadata，检索器读到的 title 全是 `Unknown`。已补 `metadatas` 并重同步。
- **检索质量实测偏低**：10 条人工 query，top-1 命中 4/10、top-3 7/10；重入/溢出/弱随机数全部落空。据此在 README 删除了"显著提升检出率"的表述，并标注"效果未验证"。
- 原验收项 `-m rag` 未落地为测试：检索依赖本地模型与 Chroma 状态，做成 pytest 会变成脆弱的环境测试；改为可重跑的探针 + 证据表。这一条属于有意偏离，需在复盘中确认。

---

### P5 — D1 决策（0.5 天，✅ 已完成 2026-10-18）

**目标**：用数据决定要不要删关键词过滤，而不是凭感觉。

| 步骤 | 内容 |
|---|---|
| 1 | 取 ≥ 20 个真实主网合约（Uniswap/Compound/Aave 等），跑 `measure_extraction.py` |
| 2 | 记录 `selected/ref` 与"被丢函数中真含漏洞的比例"（后者需要标注，做不了就只报前者） |
| 3 | 二选一：<br>• 丢弃率 < 10% → **删掉过滤**，代价可接受；<br>• 丢弃率 ≥ 10% 且预算敏感 → 保留过滤，但在报告里写明"本次仅审计 X% 的函数" |

**出口**：无论选哪边，都必须有数字支撑，并且写进 README。

**实测结果**（证据：[`evidence/p5-corpus.md`](../../evidence/p5-corpus.md)）：

- 语料：5 个仓库 / 176 文件 / 1759 函数，commit 锁定；提取回归 `1759 = 1759`（漏/噪 0）。
- 过滤丢弃率 **20.9%**（periphery 4.2% → openzeppelin 26.8%）；按原判据落在"保留"一侧。
- **但原二选一都错**：保留会让 368 个函数从账本里消失，报告会显示"提取 1391"而源码有 1759——正是 P1 消灭过的谎言。
- 实际执行第三条路：**保留过滤，把过滤项作为 `filtered / keyword_filter` 入账**；恒等式扩为四项，新增 `audit_runs.functions_filtered`（迁移 014），报告新增 "Filtered (keyword)" 行。
- 真实链路验证（项目 #62）：`3 = 0 + 2 + 0 + 1`，`helper` 在账本中显示为 filtered，报告可见。
- 未能回答：被过滤的函数里有多少真含漏洞——需要标注，属于 P6。

---

### P6 — 研究命题（唯一能回答最初问题的阶段）

**前提**：P1–P5 完成，且具备真实 LLM key（当前 `LLM_API_KEY` 为空）。

分两条支线，**按资源选一条，不要都做**：

#### 6A — 覆盖可核算性（无需真实 key，可先用故障注入）

- **命题**：现有 LLM 审计工具无法回答"哪些代码被审过、结论在何种降级下产生"；本系统对三类降级做到 100% 可追溯。
- **实验**：N ≥ 100 次故障注入，标记率 100%（Clopper–Pearson 95% 下界）；20 个合约的"已审集合"与 AST 真值集合相等。
- **能声明**：工程保证（可复现、可验证）。
- **不能声明**：检出率、SOTA 对比。这条要写清楚，否则又变成过度声明。

#### 6B — 固定预算下的调度（需 key + 费用）

- **命题**：在固定预算 B 下，按 Slither 风险分排序的调度，比文件序调度命中更多真漏洞。
- **基线**：Slither-only / LLM 文件序 / 随机 / 无预算全量。
- **数据**：SmartBugs-curated（143）或 SolidiFI 注入集。
- **指标**：recall@B、precision、每漏洞成本。
- **统计**：N ≥ 3 次重复，配对检验或 bootstrap。
- **能声明**：条件性的方法优势（有基线、有检验）。

**出口判据**：无论结果正负，都要留下可复现的实验脚本 + 原始输出 + 结论。负结果也是结果——比没有强。

---

## 4. 依赖与排期

| 阶段 | 依赖 | 工期 | 关键路径 |
|---|---|---|---|
| P0 ✅ | — | 0.5 d | |
| P1 | P0 | 1.5 d | ✔ |
| P2 | P1 + docker | 0.5 d | ✔ |
| P3 | P2 | 1.5–2 d | |
| P4 | P2 | 0.5 d | 可与 P3 并行 |
| P5 | P4 | 0.5 d | |
| P6 | P5 + key | 5–10 d | |

**总计**：P1–P5 约 4.5–5 个工作日；P6 取决于资源。

---

## 5. 每个阶段必须产出的证据

| 阶段 | 证据文件 |
|---|---|
| P0 | `evidence/extraction-baseline.md` §6 ✅ |
| P1 | `evidence/coverage-ledger.md`（恒等式测试输出 + 一份 `audit_runs` 记录导出） |
| P2 | `evidence/e2e-run.md`（链接、报告截图、四个测试套件的输出） |
| P3 | `evidence/fuzz-real.md`（counterexample + 目录哈希前后对比） |
| P4 | `evidence/kb-snapshot.md`（条目数、版本号、golden 输出） |
| P5 | `evidence/deFi-corpus.md`（语料清单 + 丢弃率） |
| P6 | `evidence/claim.md`（命题、基线、数据、统计、结论与局限） |

没有证据文件的阶段，视为未完成。

---

## 6. 明确不做

| 不做 | 理由 |
|---|---|
| 完整 Solidity 解析器 / solc AST | 实测边界准确率 99.2%，触发条件写在 spec §6.4 |
| `extra="forbid"` | 会把带额外字段的合法输出判死，提高失败率 |
| per-finding `provenance_json` | 与既有列 + run 级信息重复 |
| severity 的 DB `CHECK` 约束 | 应用层归一 + 测试足够；迁移越少越好 |
| 前端新页面 | 覆盖率用报告模板就够了 |
| 扩 SWC 知识库 | 37 条是官方全集；堆量不解决检索语义 |
| 性能优化 | 现有并发无证据表明是瓶颈；先有基线再谈 |
| 多租户 / 用户体系 | 与"审计可核算"无关 |
| 换模型 / 加 prompt 变体 | 没有基准之前，调参等于随机游走 |

---

## 7. 止损线

| 触发 | 动作 |
|---|---|
| P1 后恒等式在任一注入场景不成立 | 回滚 P1，先修恒等式，不进入 P2 |
| P2 集成测试失败 > 2 项 | 回滚到 P0 结束状态，逐个排查 |
| P3 两天内无法触发真实失败 | 把 fuzzer 降级为"实验性"，改 README，不再投入 |
| P5 语料获取失败 | 保留过滤，报告中标注覆盖率，承认局限 |
| P6 无 key / 无预算 | 只做 6A，明确声明为工程保证，不碰质量指标 |

---

## 8. 最终能声明什么（Claim Ladder）

| 层级 | 条件 | 可写进 README / 简历的句子 |
|---|---|---|
| **L0** | 现在 | 无可声明 |
| **L1** | P2 后 | "三阶段审计流水线可运行，单测/集成/E2E 全绿" |
| **L2** | P1+P2 | "审计覆盖可核算：每个函数的状态（已审/跳过/失败）与原因均可追溯" |
| **L3** | P6-A | "在 100 次故障注入下，三类降级 100% 被标记；覆盖率与 AST 真值一致" |
| **L4** | P6-B | "在固定预算 B 下，风险排序调度的 recall@B 显著高于文件序基线（p < 0.05）" |

**每一层只允许写该层的话。** 越级声明就是上一轮被指出的问题重演。

---

## 9. 现在就能做的 5 件事

1. `git add` 三份诊断文档 + 本批次代码，提交为 `[integrity-1] extraction fix`；
2. 改 README 那一行，删掉无出处的 67%；
3. 起 docker，跑一遍 20 项集成测试，确认 P0 没破坏主链路；
4. 开 P1：先写 12 条失败测试（6 类注入 + 2 条恒等式 + 4 条集成面）；
5. 把 PRR 里 ISS-03 的状态改掉。

前三件是清理，第四件是唯一有实质推进的，第五件是止损。
