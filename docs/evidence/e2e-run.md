# P2 主链路验证 · 实施证据

> 日期：2026-10-18
> 环境：Docker 29.6.1（Docker Desktop for Windows），`docker compose` 五容器
> 结论：**P0+P1 未破坏主链路；账本与报告在真实栈上自洽。**

---

## 1. 服务栈

| 容器 | 状态 |
|---|---|
| solidguard-api-1 | Up，`/health` = `{"status":"ok","checks":{"postgres":"ok","redis":"ok"}}` |
| solidguard-worker-1 | Up |
| solidguard-postgres-1 | Up (healthy) |
| solidguard-redis-1 | Up (healthy) |
| solidguard-frontend-1 | Up |

**迁移 013 已在真实 Postgres 上执行**（api 启动日志）：

```
INFO  [alembic.runtime.migration] Running upgrade 012 -> 013, add audit_runs ledger
```

`backend` 以 `./backend:/app` 挂载进容器，因此容器运行的就是工作区代码。

---

## 2. 三套测试

| 套件 | 结果 | 备注 |
|---|---|---|
| 单元 `-m "not integration and not perf"` | **138 passed** | 含 P0 的 7 条 + P1 的 25 条 |
| 集成 `-m integration` | **20 passed**（冷启动首轮 18 passed / 2 skipped） | 见 §2.1 |
| 性能 `-m perf` | **7 passed** | 见 §2.2 |

### 2.1 集成测试的首轮 SKIP 是冷启动排队

服务栈刚起来时第一次跑：`18 passed, 2 skipped`（289s）。两个 SKIP 都来自测试内的轮询超时，不是断言失败。栈热起来后立刻复跑：

```
collected 20 items
tests\test_integration.py .................... [100%]
20 passed, 145 deselected in 54.79s
```

同一批代码、同一套测试，第二轮全绿且耗时降到 1/5。判定：**冷启动时首次请求触发 JIT/连接池/镜像层预热导致的排队，不是功能缺陷**。证据留档为这次复跑；CI 上应关注首次运行的超时阈值是否需要放宽。

### 2.2 性能基准的联动修改

D3 修复后 `constructor` 成为审计单元，合成合约的单元数 +1，三处硬编码计数随之失效：

| 场景 | 原断言 | 现断言 | 处理 |
|---|---|---|---|
| A / C（2 函数合约） | `funcs == 2` | `funcs == 3` | 更新计数（2 transfer + ctor） |
| F（阈值边界） | `_make_contract(5)`，`funcs == 5` | `_make_contract(4)`，`funcs == 5` | 保持"恰好等于阈值"的语义 |
| G（10 函数并行） | `_make_contract(10)` | `_make_contract(10, include_constructor=False)` | 保留 689.6ms 历史基线可比性 |

实测（mock，50ms 固定延迟）：

```
[场景 F] 单文件 5 单元 (≤阈值)  实测 303.7ms | 理论串行 300.0ms
[场景 G] 单文件 10 单元          实测 153.3ms | 理论并行 150.0ms | 加速 4.50x
```

---

## 3. E2E（项目 #47）

| 步骤 | 结果 |
|---|---|
| 上传 `VulnerableToken.sol` | project=47，worker 处理完成 |
| Slither | **9 条检测** |
| LLM 审计 | 因 `LLM_API_KEY` 为空，4 个单元全部 `failed/llm_error`（预期降级） |
| 报告 | 生成成功，HTML 含覆盖率段与降级横幅 |

**账本行**（`audit_runs`）：

```json
{"status": "degraded", "files_total": "1", "files_processed": "1", "files_unreadable": "0",
 "functions_extracted": "4", "functions_audited": "0", "functions_skipped": "0",
 "functions_failed": "4", "invalid_findings": "0", "rag_failures": "0",
 "model": "gpt-4o", "prompt_version": "9d15319c"}
```

**两条恒等式在真实数据上成立**：

```
identity_U: 4 == 0 + 0 + 4
identity_F: 1 == 1 + 0
```

**单元明细**（`details_json.units`，按优先级排序）：

```json
[{"function": "withdraw",   "line": 23, "status": "failed", "reason": "llm_error", "rag_hits": 5},
 {"function": "transfer",   "line": 15, "status": "failed", "reason": "llm_error", "rag_hits": 5},
 {"function": "constructor","line": 9,  "status": "failed", "reason": "llm_error", "rag_hits": 5}]
```

`constructor` 出现在账本里，正是 D3 修复的直接证据；`rag_hits=5` 说明本地 embedding + Chroma 检索在没有外部 key 的情况下仍然工作。

**报告检查**：`coverage_section=true`、`degraded_banner=true`、覆盖率百分比与账本一致（0/4 = 0.0%）。

报告留档：`C:\Users\19503\AppData\Local\Temp\e2e_report_47.html`（临时目录，未入库）。

---

## 4. 这次验证证明了什么 / 没证明什么

**证明**：

1. 迁移在真实 Postgres 上可执行；
2. 空 key 的降级链路上，账本仍写出完整、可核对的一行；
3. 两条恒等式在真实数据上成立；
4. 报告的覆盖率数字来自账本，不是另算一套。

**没证明**：

1. **真实 LLM 下的行为**——`LLM_API_KEY` 为空，三态里的 `audited` 分支只在 mock 下跑过；
2. cleanup 在含 `audit_runs` 的数据上的真实执行（只有单测覆盖顺序）。

---

## 5. 对外材料同步

| 项 | 变更 |
|---|---|
| README 性能表 | 删除无出处的 `210s → 70s` / `40s → 1.7s`，改为 mock 基准实测（5.22x / 3.79x）+ 口径声明 |
| README 测试数 | 95 → 138 单测 |
| PRR ISS-01/02/03 | 更新为"已修（2026-10-18）" |
| PRR 章节标题 | "全部未修复" → "部分已修复" |
