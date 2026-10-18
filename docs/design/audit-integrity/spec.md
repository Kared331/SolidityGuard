# 审计完整性（Audit Integrity）设计说明

> 状态：**待评审**（本文档只定契约，不含代码改动）
> 日期：2026-10-18
> 适用范围：LLM 审计判定层、审计账本、报告输出、SWC 知识库
> 关联：`docs/SolidityGuard-issues-diagnosis-20260916.md`（ISS-01/02/03/06/08）、`docs/PRR-recheck-20260925.md`（审计能力可信度 🔴）

---

## 1. 一句话目标

让系统**不再说谎**：任何一次审计都能回答三个问题——审了哪些函数、哪些没审、每条结论是在什么条件下产生的——并且这三个答案由回归测试守住。

这不是新功能，是把现有能力的事实暴露出来。做完之后，README 里每一个数字才有资格被写出来。

---

## 2. 非目标（本次明确不做）

| 不做 | 原因 |
|---|---|
| 新增审计引擎 / 换模型 / 扩知识库 | 属于"加功能"，本阶段只做"补真相" |
| 前端新页面 | 除报告模板的覆盖率段落外不动前端 |
| 性能优化 | 现有并发实现保持原样 |
| Fuzzer 修复 | 单独作为第 4 刀，见 `tasks.md` |
| 重写完整 Solidity 解析器 | 实测正则阶段边界准确率 99.2%，重写属过度防御（§3.1.1、§6.4） |
| 提升检出率 | 本阶段不承诺任何质量指标，只承诺可观测性 |

---

## 3. 核心概念

### 3.1 审计单元（Audit Unit）

一个"可被独立审计的函数体"，标识为：

```
unit_key = f"{relative_file_path}#{function_name}@{line_start}"
```

#### 3.1.1 实测基线（2026-10-18）

对 `uploads/` 中已存在的 57 个去重真实文件（1,118,988 B，含 forge-std 全量 + 两个 DeFi fixture）跑当前生产代码 [`_extract_key_functions`](../../../backend/app/services/engine/llm_audit.py#L207-L275)，与"掩码 + 大括号配对"参考实现对比：

| 阶段 | 结果 |
|---|---|
| 参考真值（含函数体的单元） | **1,896** |
| 现正则阶段 | 1,905 个匹配：误报 24（22 个 interface 声明 + 2 个注释）、漏报 15（**全部**是 constructor/receive/fallback） |
| 关键词过滤后 | **1,491**（保留 78.6%，丢弃 414 = **21.7%**） |
| 被审函数体覆盖字节 | **62.4%** |

三个与直觉相反的结论：

1. **正则阶段在单元边界上准确率 99.2%**，漏报全部来自 ctor/receive/fallback。**不需要重写 Solidity 解析器**——这是本文档相对初稿的最大修正。
2. 最大损失是**关键词过滤**（21.7%），但强语料依赖：两个 DeFi fixture 上丢弃率为 **0**，forge-std 这类库里最高达 98.7%（`StdStyle.sol` 78→1）。原判断"关键词几乎恒真、过滤形同虚设"只在 DeFi 语料成立，在库语料上不成立。
3. interface 声明会**吞掉下一个 `{`**：`function balanceOf(...) external returns (uint256);` 的 body 变成后续代码（混合文件里是整个合约体），生成 body 错位的"幻影单元"。静默、且比漏报更危险——它会把无关代码当作某个函数送审。

原始数据与复现方式见 [`docs/evidence/extraction-baseline.md`](../../evidence/extraction-baseline.md)。

#### 3.1.2 判定规则

1. 单元 = **带函数体的** `function` / `constructor` / `receive` / `fallback` 声明；
2. 以 `;` 结束的声明不是单元，且扫描**必须在 `;` 处停止**（修 D2：幻影单元）；
3. 扫描前先掩码注释与字符串字面量（修 D4/D5：注释误判、字符串截断）；
4. 普通函数仍按关键词筛选（D1 **推迟修复**，避免调用量突增）；但 `constructor`/`receive`/`fallback` **永不被过滤**，关键词同时用于优先级排序；
5. **不重写完整解析器**（§3.1.1 实测边界准确率 99.2%，无必要）；触发升级为 solc AST 的条件见 §6.4。

### 3.2 审计账本（Audit Ledger）

一次 LLM 审计任务 = 一条 `audit_run` + N 条单元记录。账本必须满足：

```
functions_extracted == functions_audited + functions_skipped + functions_failed + functions_filtered
```

这条恒等式是整个方案的锚点。任何破坏它的代码路径都是 bug。

### 3.3 结论（Finding）

只有 `status=audited` 的单元才可能产出 Finding。失败与跳过**永远不进入 findings 表**，只进入账本。这是 I3 不变量的来源。

---

## 4. 接口契约

### 4.1 函数提取

```python
# backend/app/services/engine/solidity_units.py（新增，约 60–80 行）

@dataclass(frozen=True)
class FunctionUnit:
    name: str
    kind: Literal["function", "constructor", "receive", "fallback"]
    line_start: int          # 1-based
    line_end: int            # 1-based
    body: str                # 含大括号的原始片段
    priority: int            # 关键词命中数，仅用于排序

def extract_functions(source: str) -> list[FunctionUnit]: ...
```

**实现要求**：

- 先做**掩码化**：把注释（`//`、`/* */`）与字符串字面量（`"..."`、`'...'`）替换为等长空格，保留原始偏移，再在掩码文本上扫描；
- 匹配到签名后，先在掩码文本中找 `{` 或 `;`：先遇到 `;` 即判定为声明，**不生成单元**（这是 D2 的修法）；
- 大括号配对必须处理嵌套（`for`/`if`/内联结构体）；
- 行号由偏移换算，不依赖正则行匹配；
- 纯函数、无 I/O、无外部依赖，可被单测直接调用。

**验收样例**（全部来自实测缺陷，见 6.1）：

| 输入特征 | 期望 | 对应缺陷 |
|---|---|---|
| 注释里出现 `function fake() {` | 不计为单元 | D4 |
| 字符串 `require(x, "}")` | 该函数 body 完整，不提前截断 | D5 |
| `constructor(uint256 supply)` | 计为单元 | D3 |
| `receive() external payable { ... }` | 计为单元 | D3 |
| `fallback() external { ... }` | 计为单元 | D3 |
| 接口声明后紧跟实现（混合文件） | 声明不生成单元，且**不吞掉**后续 `{` | D2 |
| 函数体内嵌套 `for { if { } }` | body 截取完整 | — |

### 4.2 数据模型（迁移 013）

**新增表 `audit_runs`**

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | int PK | |
| `project_id` | int FK(projects.id), index | |
| `status` | String(20) | `running` / `completed` / `degraded` / `failed` |
| `model` | String(100) nullable | 实际使用的模型 ID |
| `prompt_version` | String(50) nullable | 提示词模板哈希前 8 位 |
| `kb_version` | String(50) nullable | SWC 快照哈希，见 §5 |
| `files_total` | int | 参与审计的 `.sol` 文件数 |
| `files_processed` | int | 成功读取的文件数 |
| `files_unreadable` | int | 读不了的文件数（满足 F 恒等式） |
| `functions_extracted` | int | 分母（仅 processed 文件） |
| `functions_audited` | int | 分子 |
| `functions_skipped` | int | |
| `functions_failed` | int | |
| `functions_filtered` | int | 被关键词过滤、未送审的函数数（P5 加入：不入账则分母缩水） |
| `invalid_findings` | int | severity 非法被丢弃的条目数 |
| `rag_hits` | int | 检索命中条数 > 0 的函数数 |
| `rag_failures` | int | 检索抛异常的函数数 |
| `details_json` | JSON nullable | 逐单元账本（见下） |
| `started_at` / `finished_at` | DateTime | |

`details_json` 形状（便于报告直接渲染，避免 N+1 查询）：

```json
{
  "units": [
    {"file": "contracts/Token.sol", "function": "withdraw", "line": 23,
     "status": "audited", "reason": null, "findings": 2, "rag_hits": 3, "truncated": false},
    {"file": "contracts/Token.sol", "function": "setFee", "line": 61,
     "status": "skipped", "reason": "budget", "findings": 0, "rag_hits": 0, "truncated": false}
  ]
}
```

**`llm_audit_results` 增列**

| 列 | 类型 | 说明 |
|---|---|---|
| `audit_run_id` | int FK(audit_runs.id) nullable, index | 旧数据为 NULL |

> 不新增 per-finding 的 `provenance_json`：文件/函数已是本表列，模型/提示词/知识库版本是 run 级信息，重复存一遍属过度设计。溯源按 §4.4 推导。

**`severity` 取值收紧**：`Critical` / `High` / `Medium` / `Low` / `Informational`（与 [`AuditFindingSchema`](../../../backend/app/llm/schemas/audit_output.py#L11-L21) 的 `Literal` 对齐）。可选加 `CHECK` 约束；若不加深，则由应用层归一 + 单测守卫。

### 4.3 审计运行结果

`execute_single_file` 的返回值按文件聚合，任务层再合并（`LLMAuditEngine.execute()` 是死代码，P1 删除）：

```python
# execute_single_file 返回值
{
    "findings": [...],          # 仅 status=audited 的单元产出
    "units": [                  # 新增：逐单元账本
        {"name": "withdraw", "line": 23, "status": "audited", "reason": None,
         "findings": 2, "rag_hits": 3}
    ],
    "files_processed": int,     # 0 或 1
    "files_unreadable": int,    # 0 或 1
    "rag_failures": int,
    "audit_run_id": int,        # 由任务层回填
}
```

任务层合并后写入 `audit_runs`，并计算：

```
degraded = (skipped + failed + files_unreadable) > 0 or rag_failures > 0
```

### 4.4 溯源（不新增列）

一条 Finding 的溯源由三段拼出，不额外存储：

| 段 | 来源 |
|---|---|
| `file` / `function` | `llm_audit_results` 已有列 |
| `model` / `prompt_version` / `kb_version` | 经 `audit_run_id` 关联 `audit_runs` |
| `rag_hits` / `context_truncated` | `audit_runs.details_json` 中同一 `unit_key` 的记录 |

即：

```
finding → audit_run_id → (model, prompt_version, kb_version)
        → (contract_name, function_name) → details_json[unit_key] → (rag_hits, truncated)
```

优点：零冗余、零迁移风险；缺点：按函数查 provenance 需要应用层 join，报告渲染一次即可接受。

用途：报告可点击溯源；后续路线 A（可核算的审计完整性）直接以此为实验对象。

### 4.5 输出契约

1. **findings 中不允许出现 `severity="unknown"`**。当前 [llm_audit.py:339](../../../backend/app/services/engine/llm_audit.py#L339)、[L357](../../../backend/app/services/engine/llm_audit.py#L357) 把基础设施故障伪装成结论，[L383](../../../backend/app/services/engine/llm_audit.py#L383) 又在 LLM 缺字段时补默认值 `unknown`，三处都必须删除。
2. LLM 返回的 severity 做大小写归一；无法归一 → 该条不落库，计入 `fail_reasons.parse_error`，账本可见。
3. 报告新增"审计覆盖与完整性"段（HTML 与 DOCX 同步），内容：

| 字段 | 呈现 |
|---|---|
| 提取函数数 / 已审 / 跳过 / 失败 | 表格 |
| 跳过与失败的原因分布 | 表格 |
| 覆盖率 | `audited / extracted`，< 100% 时红色标注 |
| 降级状态 | `degraded=true` 时在报告顶部加横幅 |
| 模型 / 提示词版本 / 知识库版本 | 页脚 |

---

## 5. SWC 知识库

**问题**：当前 [`swc_sync.py`](../../../backend/app/services/engine/swc_sync.py) 每次运行时从已归档的 GitHub 仓库拉取 37 个文件并正则解析，网络失败即知识库为空，且无版本概念。

**方案**：

1. 生成一次性离线快照 `backend/app/services/engine/data/swc_registry.json`，字段：`swc_id / title / description / severity / code_example`，条目数 **37**（SWC 官方全集，不多不少）；
2. `kb_version = "swc-" + sha256(snapshot)[:8]`，写入 `audit_runs.kb_version`（Finding 经 `audit_run_id` 溯源）；
3. 同步逻辑默认读快照；显式 `refresh=true` 才走网络，且拉取结果必须通过 schema 校验与条目数校验后才落库；
4. upsert 幂等（按 `swc_id` 唯一键），重复同步不产生重复条目；
5. **检索回归基线**：固定 10 条 `(函数片段 → 期望 top1 swc_id)` 用例，作为 `-m rag` 标记的测试，守护"检索结果不漂移"。不承诺相关性提升，只承诺可复现。

> 预期管理：37 条通用描述不可能显著提升检出率，本阶段不为它做任何效果声明。

---

## 6. 不变量与验收用例

### 6.1 I1 覆盖守恒

**命题**：对任意输入，提取结果等于解析真值，且 `audited + skipped + failed + filtered == extracted`。

| 用例 | 断言 | 对应缺陷 |
|---|---|---|
| 注释里含 `function x() { ... }` | 不产生单元 | D4 |
| 字符串含 `}` | 该函数 body 完整（长度与参考一致） | D5 |
| 接口声明 + 同文件实现 | 声明不生成单元，实现 body 完整 | D2 |
| `constructor` / `receive` / `fallback` | 均被提取并送审 | D3 |
| 真实 fixture `VulnerableToken.sol` | 单元集合 == {constructor, transfer, withdraw, getBalance} | D3 |
| 无关键词函数（如 `helper()`） | 仍在送审集合内 | D1 |
| 预算耗尽 | `audited + skipped == extracted`，skipped.reason == budget | — |
| 关键词过滤 | 被过滤函数 `status=filtered, reason=keyword_filter`，且计入 `extracted` | D1 |

### 6.2 I2 降级可见

**命题**：三类降级 100% 带原因，无静默路径。

| 注入方式 | 断言 |
|---|---|
| `token_budget.check_budget → False` | 单元 `status=skipped, reason=budget`；`run.status=degraded` |
| 检索批量与逐条均抛异常 | 单元 `status=audited` 但 `rag_failures > 0`；报告含降级横幅 |
| 文件读取 `OSError` | 该文件全部单元 `status=failed, reason=read_error` |
| LLM 抛异常 | 单元 `status=failed, reason=llm_error`；findings 不新增 |

### 6.3 I3 结论不混流

**命题**：失败不进 findings，severity 合法。

| 检查 | 方法 |
|---|---|
| 不存在 `severity=unknown` | 全量单测 + DB 查询断言 |
| 失败条目不在 findings | 故障注入后 `len(findings)` 不增加 |
| 报告覆盖率段存在且数字自洽 | 渲染后断言 HTML 含表格与恒等式 |

### 6.4 回归基线

改造前后跑同一批 fixture，记录：提取函数数、送审函数数、finding 数。**预期 finding 数会上升**（因为 constructor/receive/fallback 与无关键词函数进入审计），这是修正而非退化；报告中需说明口径变化。

**升级为 solc AST 的触发条件**（现在不做，满足任一才做）：

1. 在 DeFi 语料（≥ 20 个真实主网合约）上，单元边界噪声 > 5%；
2. 出现无法用掩码修复的 body 错位（例如内联汇编、`unicode"..."` 字面量）；
3. 需要跨函数/跨合约数据流分析——那是另一个问题，不属于本阶段。

---

## 7. 兼容与回滚

- 迁移 013 只做加法（新表 + 两个 nullable 列），旧数据 `audit_run_id=NULL`，读取端用 `getattr(..., None)` 兼容；
- 历史 `severity` 的小写值（如 `high`）**不改写**，读取端统一归一化后再渲染，避免数据迁移风险；
- 报告模板对 `coverage=None` 时整段不渲染（旧报告重渲染不报错）；
- 回滚：`alembic downgrade -1`；代码回滚到改造前 commit 即可，无数据迁移依赖；
- API 契约只增字段（`coverage`、`audit_run_id`），不删不改既有字段。

---

## 8. 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 词法解析仍有边角 case | 单元漏检 | 用 fixture + 合成用例表驱动；解析器与审计引擎解耦，可单独替换为 solc AST |
| finding 数上升被误读为"变好了" | 对外口径失真 | 报告显式标注"覆盖口径变化"，本阶段不做质量声明 |
| 账本写入增加 DB 压力 | 任务变慢 | `details_json` 单行写入，不做逐单元 insert |
| 与并行执行竞争 | 计数错乱 | 账本在收集阶段用线程安全累加（`Lock` 或 future 返回值汇总），不共享可变 dict |

---

## 9. 完成判定（DoD）

1. 三条不变量各有对应单测，且**先红后绿**；
2. `pytest -m "not integration and not perf"` 全绿，新增测试约 15 条（其中提取器 ≥ 7）；
3. 对 `VulnerableToken.sol` 跑一次（可用 mock LLM），报告含覆盖率段且恒等式成立；
4. **重跑测量脚本**：`extracted == reference`（missed 0 / noise 0 / body_mismatch 0），ctor/receive/fallback 全部提取；`selected/ref` 预计仍在 ~79%（D1 推迟，属已知缺口）；数字写入 `docs/evidence/extraction-baseline.md`；
5. `docs/PRR-recheck` 中 ISS-01/02/03 状态可被更新为"已修复（有测试）"；
6. 本阶段不新增任何质量/性能宣称。
