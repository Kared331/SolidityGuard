# P1 账本与可见性 · 实施证据

> 日期：2026-10-18
> 范围：blueprint §P1
> 状态：**代码完成，端到端未验证**（docker 未启动）

---

## 1. 变更清单

| 文件 | 变更 |
|---|---|
| `backend/app/models/audit.py` | 新增 `AuditRun`；`LLMAuditResult` 增 `audit_run_id` |
| `backend/app/models/__init__.py` / `project.py` | 导出与关系 |
| `backend/alembic/versions/013_add_audit_runs.py` | 新表 + 新列 + FK + 索引 |
| `backend/app/services/engine/llm_audit.py` | 状态/原因返回；`normalize_severity`；删除 `execute()`；injection 转为 warning；`PROMPT_VERSION` |
| `backend/app/tasks/run_llm_audit.py` | `build_coverage`；建 run → 汇总 → 落账本；异常标 failed |
| `backend/app/tasks/cleanup.py` | 抽出 `_delete_project_rows`，补 `audit_runs` 删除（FK 顺序） |
| `backend/app/services/report_generator.py` | `coverage_from_run`；最新 run 过滤；`polish` 保留额外键 |
| `backend/app/services/templates/report.html.jinja2` | 覆盖率段 + 降级横幅 |
| `tests/test_audit_integrity.py` | 25 条验收测试 |

---

## 2. 测试

`tests/test_audit_integrity.py`：**25 passed**

| 组 | 条数 | 覆盖 |
|---|---|---|
| 失败矩阵 | 6 | 正常 / 预算 / LLM 异常 / 解析失败 / RAG 失败 / 文件不可读 |
| 恒等式 | 6（参数化） | F 与 U 同时成立 |
| 报告 | 5 | 最新 run、旧数据回退、覆盖率一致、HTML 渲染、polish 保键 |
| 清理 | 1 | findings 先于 runs 删除 |
| 迁移 | 1 | 单一 head，013 接 012 |
| 引擎层 | 3 | 真跑 fixture，验证 audited/skipped/failed 三态 |
| severity | 3 | 小写归一、UNKNOWN 拒绝、缺失拒绝 |

全量：**138 passed**（原 113 + 25），`ruff check backend` 与 `ruff format --check backend` 均通过。

---

## 3. 实施期的三个真实发现

这几条不在计划里，是写代码/跑测试时被逼出来的。

### 3.1 `execute()` 不是普通死代码，它是抽象方法

删除后测试直接报：

```
TypeError: Can't instantiate abstract class LLMAuditEngine with abstract method execute
```

`BaseEngine(ABC)` 强制所有引擎实现 `execute(*args, **kwargs)`。所以"删死代码"实际是**解除继承关系**：`LLMAuditEngine` 的并行单位是文件，项目级 fan-out 在任务层。已在类 docstring 写明理由。

**教训**：蓝图里写"删掉 execute 即可"是错的；不读 `base.py` 就会在第一步卡住。

### 3.2 校验顺序让归一化永远不执行

原代码先用 `AuditFindingSchema` 校验，而 schema 的 `severity` 是 `Literal["Critical", ...]`。LLM 返回 `"high"` 时，**校验先失败、finding 被丢弃**，后面新加的 `normalize_severity` 根本没机会跑。

引擎级测试（fixture + 假 LLM 返回 `"high"`）抓到了这个顺序错误。修法：先归一、再校验。

**教训**：只测 `normalize_severity("high") == "High"` 会全绿，但生产路径仍然是坏的。测试必须穿过真实调用链。

### 3.3 F 恒等式抓到了我自己写错的测试

参数化用例里有一条 `(processed=1, unreadable=1)` 且 `files_total=1`——同一文件既处理又不可读。实现拒绝了这个输入，测试红了。

问题在测试，不在实现。但正好证明 F 恒等式的价值：**它能让你无法靠"少计一个文件"把账做平**。

---

## 4. 尚未验证

| 项 | 原因 | 影响 |
|---|---|---|
| 迁移在真实 Postgres 上执行 | docker 未启动 | 013 只在脚本层面校验过 head 链，未 `upgrade head` |
| 20 项集成测试 | 同上 | `run_llm_audit` 的 DB 写入路径未被真实 session 覆盖 |
| E2E（上传→审计→报告） | 同上 | 报告模板只渲染过构造数据 |
| 真实 LLM 调用 | `LLM_API_KEY` 为空 | 三态是 mock 出来的，不是真实模型行为 |

这些属于 **P2** 的出口判据，不是 P1 的代码缺口。

---

## 5. 现在能说什么（Claim Ladder）

- **L1 未达成**：E2E 没跑。
- **L2 部分达成**：账本与报告在构造数据上自洽；需 P2 的 E2E 才能宣称"可核算"。

在 P2 通过之前，README / 简历不应写任何覆盖率或完整性结论。
