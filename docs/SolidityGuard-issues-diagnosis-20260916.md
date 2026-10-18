# SolidityGuard 审计引擎健壮性走查 · 详细问题清单

> 生成日期：2026-09-16（首版）
> 追补日期：2026-09-16（第二轮：Slither / Foundry 外部工具引擎走查）
> 性质：只读诊断（未改动任何代码）
> 范围：LLM 审计引擎 `app/services/engine/llm_audit.py`、**外部工具引擎 `app/services/engine/slither.py` / `fuzzer.py`**、任务层 `app/tasks/run_slither.py` / `run_fuzzer.py`、测试与 fixture

---

## 一、总览

| 严重度 | 问题 | 编号 | 是否影响审计能力 |
|---|---|---|---|
| 🔴 高 | 预算不足 = 静默丢函数 | ISS-01 | 影响"结果可信度" |
| 🔴 高 | RAG 大面积失败时静默降级为裸 LLM | ISS-02 | 直接压低召回 |
| 🟡 中 | 函数提取正则遗漏真实函数 | ISS-03 | 结构性压低召回 |
| 🟡 中 | 读文件无大小上限校验 | ISS-04 | 稳定性风险 |
| 🟡 中 | 双轨架构（同步引擎 + 异步 pipeline） | ISS-05 | 维护性/行为漂移 |
| 🟡 中 | 测试偏 mock，未证明审计能力 | ISS-06 | 误判"能力低" |
| 🔴 高 | Fuzzer 生成测试失能（编译失败 / 无断言） | ISS-07 | 假阴性 100%，掩盖真实风险 |
| 🔴 高 | Slither solc 回退对跨文件 import 项目静默全空 | ISS-08 | 能力失效但全绿 |
| 🟡 中 | Slither `raw_result` 与 detections 数据不一致 | ISS-09 | 报表/结果不对应 |
| 🟡 中 | `forge init --force` 污染用户项目目录 | ISS-10 | 数据污染 / 并发覆盖 |
| 🟡 中 | Foundry `-vvv` 输出无上限入 DB | ISS-11 | 超大字段风险 |
| 🟡 中 | Fuzz 结果无法映射回漏洞/风险类型 | ISS-12 | 上下文断裂，结论不可用 |

---

## 二、详细问题

### ISS-01｜预算不足 = 静默丢函数，无用户可见信号

- **文件**：`backend/app/services/engine/llm_audit.py`
- **位置**：`_audit_single_function` 顶部（`check_budget` 返回 False 分支）；`execute_single_file` 中 `audited` 计数逻辑
- **现状**：
  ```python
  ok, _ = token_budget.check_budget(project_id)
  if not ok:
      return [], False   # 静默返回空
  ```
  调用方仅当 `audited=True` 才累加 `functions_audited`。被跳过函数既不计入审计数，也不产生任何用户提示。
- **影响**：预算耗尽后，用户看到"审计完成、0 漏洞"，无从分辨是"真没漏洞"还是"被预算跳过"。
- **风险评级**：🔴 高
- **修复建议**：
  1. 增加静态计数器（如 `skipped_functions`），或让 `_audit_single_function` 返回带原因的跳过标记。
  2. 在最终 result 中暴露 `skipped_count` 与 `skip_reason=budget`。
  3. 前端/报告视图提示"因 Token 预算不足，N 个函数未审计"。

### ISS-02｜RAG 大面积失败时静默降级为裸 LLM

- **文件**：`backend/app/services/engine/llm_audit.py`
- **位置**：`execute_single_file` 批量 embedding/RAG 的 `except` 回退段
- **现状**：批量失败会逐条回退，`except` 吞掉异常后 `rag_contexts[i]="None found"`，不记录失败条数。
- **影响**：RAG 故障时审计以"无上下文"继续，输出与有上下文时接近，但**完全无迹可查**，且系统性降低审计质量。
- **风险评级**：🔴 高（能力影响 + 不可观测）
- **修复建议**：
  1. 统计 RAG 成功/失败条数（如 `rag_hits`、`rag_failures`）。
  2. 失败占比达阈值时在结果里标记 `degraded: true` / `reason: rag_unavailable`。
  3. 保留现有逐条回退逻辑，但增加日志与结果字段。

### ISS-03｜函数提取正则遗漏真实函数

- **文件**：`backend/app/services/engine/llm_audit.py`
- **位置**：`_extract_key_functions`（`function\s+(\w+)` 正则 + keywords 白名单）
- **现状**：
  - 正则不匹配"函数声明换行/修饰符前置"等写法。
  - **不含关键词表内关键字的函数直接跳过审计**（keywords 白名单判定）。
  - 不处理 Solidity 0.8 `receive()`、自定义 error 等。
- **影响**：大量真实函数没进审计队列，系统性拉低 recall——这是"能力看起来低"的结构性原因，优先于模型本身。
- **风险评级**：🟡 中（但对 recall 是结构性上限瓶颈，实际影响高）
- **修复建议**：
  1. 用 Solidity AST/解析器（如 `solc` 编译 json、`py-solc-x` 或 slither 输出）代替正则提取函数。
  2. 若保留正则，需支持多行声明、修饰符、`receive/fallback`。
  3. **评估口径上必须区分**："正则漏函数"（ISS-03）与"模型没识别函数内漏洞"（模型真能力）。

### ISS-04｜读文件无大小上限校验

- **文件**：`backend/app/services/engine/llm_audit.py`
- **位置**：`execute_single_file` 读取 `content = f.read()`，后经 `_sanitize_source_code` 截断到 8000
- **现状**：整文件先读入内存再进行截断，无文件大小前置校验。
- **影响**：超大 `.sol` 文件占用内存高，极端情况影响稳定性。
- **风险评级**：🟡 中
- **修复建议**：读取前检查 `os.path.getsize`，超过阈值（如 1MB）提前拒绝或仅读前 N 字节。

### ISS-05｜双轨架构：同步引擎 + 异步 pipeline 并存

- **文件**：
  - 生产路径：`backend/app/services/engine/llm_audit.py`（同步，被调用）
  - 闲置：`backend/app/llm/pipeline/audit_pipeline.py`（异步下一代，注释标注"未被生产路径调用"）
- **现状**：`audit_pipeline.py` 顶部注明"架构状态：下一代异步 pipeline，当前未被生产路径调用。生产路径：app.services.engine.llm_audit.LLMAuditEngine"。SSE 流式通过 `llm/pipeline/stream.py` 被同步路径借用。
- **影响**：两套实现并存 → 改一处漏一处、行为漂移、维护成本高。
- **风险评级**：🟡 中（维护性）| 架构债
- **修复建议**：**迁移前先修 ISS-01/ISS-02**（避免把 bug 一起搬进异步 pipeline），收敛为单一路径后冻结/删除旧引擎。

### ISS-06｜测试偏 mock，未证明审计能力

- **文件**：`tests/test_engines.py`、`tests/test_llm_resilience.py`、`tests/conftest.py`
- **现状**：
  - `test_engines.py` 顶部 `sys.modules[mod_name] = MagicMock()` 批量 mock。
  - 大量"审计结果"测试用假数据灌 mock，断言 mock 原样返回（`result == data`），只验证传参透传，**未验证模型能否识别真实漏洞**。
  - `test_llm_resilience.py` 自述"V5 mock 双轨——无真实 key 时的覆盖"。
  - 强项：安全类测试（Zip Slip / Tar Slip / 路径穿越）真实且高强度；JSON 5 层回退有 mock 用例。
- **影响**：测试"全绿"造成能力假象，与 ISS-03 叠加，放大"真实能力低"的误判。
- **风险评级**：🟡 中（能力验证缺失）
- **修复建议**：新增"真实能力基准"，而非只靠 mock。

### ISS-07｜Fuzzer 生成测试失能（编译失败 / 无断言）—— 本轮最重要发现

- **文件**：`backend/app/services/engine/fuzzer.py`
- **位置**：`_generate_fuzz_test`（测试生成）；`execute`（`forge test` 运行）
- **现状**（结构性缺陷，两条叠加）：
  1. **生成的测试大概率编译不通过**：
     - `{var_name} = new {cname}()`（`fuzzer.py` 生成段）——构造函数带参数的合约直接编译失败。`fixtures/VulnerableToken.sol` 是 `constructor(uint256)`，恰好命中。
     - 所有调用一律 `{func}(x)` 只传一个 `uint256 x`，不管函数真实签名。`transfer(address,uint256)` 会被生成为 `transfer(x)`，编译失败。
  2. **即使编译通过，逻辑上也是空转**：每个调用都被 `try/catch` 包裹，`catch` 内无任何断言（注释"reverted is expected"）。唯一有断言的 `testFuzz_basic` 是 `assertEq(x,x)`，恒真。
- **影响**：Fuzzer 产出的 `FuzzingResult` **假阳性为零、假阴性 100%**——它永远不会报漏洞。结果是"fuzz 全绿"并非项目安全，而是**测试本身失去探测能力**，系统性掩盖真实风险。
- **风险评级**：🔴 高（这是用户直觉中"大问题但没找出来"的那个）
- **修复建议**：
  1. 生成测试前解析真实函数签名（参数类型集），按签名生成调用；构造函数需带参数。
  2. 放弃"全 try/catch 吞掉"模式，改为**对关键不变量断言**（如 `assert(余额守恒)`、`assert(不小于前值)`），让 forge fuzz 真正能触发并暴露不一致。
  3. fuzz 方向应对准 Slither/LLM 已标记的高危函数，而非任意前 5 个。

### ISS-08｜Slither solc 回退对跨文件 import 项目静默全空

- **文件**：`backend/app/services/engine/slither.py`
- **位置**：`_run_slither_file`（`--compile-force-framework solc`）→ `execute` 中 fallback 分支
- **现状**：对单个 `.sol` 文件用 `--compile-force-framework solc` 强编译。合约一旦 `import` 本地其他文件，solc 单文件编译失败 → 返回 `{"error": ...}` → `dets` 为空列表 → 结果**静默 0 检测**，无警告、无降级标记。
- **影响**：真实项目几乎都跨文件 import，这条 fallback 路径对插件化合约库 = 分析结果为空且不报错。与 ISS-02（RAG 静默降级）同一类病——能力失效但全绿。
- **风险评级**：🔴 高（能力失效 + 不可观测）
- **修复建议**：
  1. 单文件 solc 失败时记录计数并标记 `degraded: true` / `reason: solc_import_failed`。
  2. 对含 import 的项目优先走 `_run_slither_dir`（框架自动检测），而非逐文件 solc。
  3. 结果里回传失败文件清单与原因。

### ISS-09｜Slither `raw_result` 与 detections 数据不一致

- **文件**：`backend/app/services/engine/slither.py`
- **位置**：`execute` 返回值（`first_result` 仅取第一个 root，detections 为全项目累计）
- **现状**：仅把 `first_result`（第一个 project root 的原始结果）作为 `raw_result` 入库，而检测列表是所有 project_roots 累计。多 root 项目时 DB 存的 raw_result 与 detections 对不上。
- **影响**：报表/审计展示里"原始结果"与"检测列表"口径不一致，可能误导排查。
- **风险评级**：🟡 中
- **修复建议**：`raw_result` 合并所有 root 结果，或明确按 root 拆分存储并保持一对一对齐。

### ISS-10｜`forge init --force` 污染用户项目目录

- **文件**：`backend/app/services/engine/fuzzer.py`
- **位置**：`execute`（`forge init --no-git --force`）与 `_generate_fuzz_test` 写入测试文件
- **现状**：用 `--force` 初始化并把生成的测试文件直接写进用户上传的项目目录。并发/重复跑 fuzz 会互相覆盖；已含 `test/*.sol` 的项目被添加多余文件；`--force` 可能清掉已有配置。
- **影响**：污染差异/用户项目数据，重复任务下行为不确定。
- **风险评级**：🟡 中
- **修复建议**：在工作副本/临时目录执行 forge 与生成测试，避免修改原始项目目录；必要时先备份或检测已有配置文件。

### ISS-11｜Foundry `-vvv` 输出无上限入 DB

- **文件**：`backend/app/services/engine/fuzzer.py`、改造调用方 `app/tasks/run_fuzzer.py`
- **位置**：`execute` 中 `forge test -vvv`，`raw_output` 整体入库
- **现状**：`-vvv` 全量输出无截断，直接存 `FuzzingResult.raw_output`。大项目输出可达数百 KB，存在超大字段/内存风险。
- **影响**：超大字段、DB 膨胀、查询缓慢。
- **风险评级**：🟡 中
- **修复建议**：限制 `raw_output` 长度（如截断到 64KB），或只保留 `[FAIL]`/Counterexample 相关行。

### ISS-12｜Fuzz 结果无法映射回漏洞 / 风险类型

- **文件**：`backend/app/services/engine/fuzzer.py`、`app/tasks/run_fuzzer.py`、`app/models.py`
- **位置**：`failures` 仅存 `test_name + counterexample`
- **现状**：fuzz 失败结果只记录测试名与反例输入，**不关联合约、风险类型（如重入/溢出）**，前端/报告无法据此产出有意义的安全结论。即便 ISS-07 修好，这层上下文也是断的。
- **影响**：fuzz 发现无法转化为可操作的安全告警，价值大幅缩水。
- **风险评级**：🟡 中
- **修复建议**：`failures` 增加 `contract`、`function`、`risk_type` 字段，并在模型层落库；前端据此聚合展示。

---

## 三、P1 真实能力基准 · 可行性分析（本轮未执行）

### 3.1 现状
- `tests/fixtures/VulnerableToken.sol`：含 2 处真漏洞（SWC-101 整数溢出、SWC-107 重入），注释已标注。
- `tests/fixtures/SimpleToken.sol`：默认"安全"基线合约。
- `tests/fixtures/test_contracts.zip`：供上传测试。

### 3.2 起步可行性
- **可行**：现有 VulnerableToken.sol + SimpleToken.sol 可立即跑一次真 LLM 实验，判断"模型能否识别 SWC-101/SWC-107"。
- 若识别出 → 潜在能力在，瓶颈主因是 ISS-03（函数提取漏检）。
- 若未识别 → 才是模型层能力问题。

### 3.3 完整基准须注意的陷阱
| 项 | 现状 | 建议 |
|---|---|---|
| 真值来源 | 合约注释标注 | 起步够用；完整基准须用官方审计报告作 ground truth |
| 规模 | 1 合约 / 2 漏洞 | 不足以算有意义 recall，需扩充到 10+ 契约 |
| 评估口径 | 未定义 | 建议四个指标：真候选召回率、误报率、预算内完成率、静默跳函数率（新增） |
| ISS-03 影响 | 会拉低 recall | 跑前先分区统计："正则漏函数" 与 "模型未识别" 分开计数 |

---

## 四、优先级建议（待批准，尚未执行）

1. **ISS-07** Fuzzer 测试失能 —— **本轮最高优先级**，假阴性 100%，先修
2. **ISS-01** 静默跳函数计数 —— 改动小、影响大
3. **ISS-08** Slither solc 回退静默全空 —— 能力失效但全绿
4. **ISS-02** RAG 降级可见性 —— 次之
5. **ISS-10/11/12** Fuzz 目录污染 / 输出上限 / 结果映射 —— 随 ISS-07 一起处理
6. **ISS-09** Slither raw_result 对齐 —— 独立
7. **ISS-05** 双轨收敛 —— **须在 ISS-01/02/07/08 修复后**再做（避免 bug 搬家）
8. **P1 基准** —— 可与上项并行，用现有 fixture，无需等前项完成

> 提示：ISS-07 / ISS-08 属于外部工具引擎（静态/模糊层），与本轮发现的 LLM 层问题（ISS-01~06）性质不同——**前者是"跑但没测出"，后者是"跑了但静默降级"**，两类都压低了"真实能力"，均会让报告看起来"全绿却不可信"。

---

## 五、参考文件索引

- 生产引擎：`backend/app/services/engine/llm_audit.py`
- **Slither 引擎**：`backend/app/services/engine/slither.py`、`backend/app/tasks/run_slither.py`
- **Foundry/Fuzz 引擎**：`backend/app/services/engine/fuzzer.py`、`backend/app/tasks/run_fuzzer.py`
- 任务调度：`backend/app/tasks/run_llm_audit.py`、`backend/app/tasks/pipeline.py`
- 调度抽象/幂等：`backend/app/services/task_dispatcher.py`
- 异步空闲 pipeline：`backend/app/llm/pipeline/audit_pipeline.py`
- SSE 流式：`backend/app/llm/pipeline/stream.py`
- 测试：`tests/test_engines.py`、`tests/test_llm_resilience.py`
- fixture：`tests/fixtures/VulnerableToken.sol`、`SimpleToken.sol`

*本文档为只读诊断产物，不含任何代码修改。*