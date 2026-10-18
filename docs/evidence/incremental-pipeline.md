# 增量审计全链路 · 实施证据

> 日期：2026-10-18
> 范围：选题 A 的六个功能（diff 解析 → 映射 → 调度 → 影响面 → CI → 报告对比）
> 结论：**六个功能全部跑通；真实链路 8 个函数 → 只审 1 个，7 个计入 unchanged。**

---

## 1. 六个功能的落点

| 功能 | 实现 | 状态 |
|---|---|---|
| 1. git diff 解析 | `services/incremental/diff_parser.py` | ✅ |
| 2. 函数级变更映射 | `services/incremental/mapper.py` | ✅ |
| 3. 增量调度（复用优先级与预算） | `POST /projects/{id}/incremental-audit` → `tasks/run_incremental_audit.py` → `execute_single_file(only_units=...)` | ✅ |
| 4. 变更影响面提示 | `audit_runs.details_json.incremental`（changed / unchanged / whole_file / hunks）+ 报告 Unchanged 行 | ✅ |
| 5. CI 触发 | `.github/workflows/solidguard-incremental.yml.example` | ✅ 模板 |
| 6. 两次报告对比 | `GET /runs/{base}/compare/{head}` | ✅ |

---

## 2. 真实链路（项目 #68）

上传含两个合约的 zip（8 个函数），先全量、再增量。增量 diff 只改 `withdraw` 一行。

| 运行 | extracted | audited | unchanged | findings |
|---|---|---|---|---|
| A 全量 | 8 | 8 | 0 | 21 |
| B 增量 | 8 | **1** | **7** | 3 |

计划明细（`details_json.incremental`）：

```json
{"files": [{"file": "VulnerableToken.sol",
            "changed": ["withdraw"],
            "unchanged": ["constructor", "transfer", "getBalance"],
            "whole_file": false, "hunks": 1}],
 "missing": [],
 "changed_total": 1,
 "unchanged_total": 7}
```

对比接口：

```json
{"counts": {"added": 1, "removed": 19, "persisted": 2}}
```

报告渲染包含 `Unchanged (not in diff)` 行。

**一个中途修正**：第一版增量运行只把 diff 涉及的文件计入账本（`extracted=4`），未触及的文件完全不出现——这会让覆盖率分母缩水，正是 P5 修过的同类问题。改为"所有文件入账、未触及记为 unchanged、但不调用模型"。

---

## 3. 接口

```http
POST /api/v1/projects/{id}/incremental-audit
X-API-Key: ...
Content-Type: application/json

{"diff": "<unified diff text>", "path_map": {"contracts/Token.sol": "Token.sol"}}
```

- `path_map` 可选：单文件上传会被哈希重命名，zip/tar 上传保留相对路径；
- 路径先精确匹配，再走 `path_map`，最后按唯一 basename 兜底；
- 映射不上的路径记入 `details_json.incremental.missing`，不会静默忽略。

```http
GET /api/v1/runs/{base_run_id}/compare/{head_run_id}
```

返回 `added / removed / persisted` 与两次运行的覆盖数字。

---

## 4. CI 触发

模板：`.github/workflows/solidguard-incremental.yml.example`

```bash
git diff --no-color "origin/$BASE...HEAD" -- '*.sol' > diff.patch
jq -Rs '{diff: .}' diff.patch > payload.json
curl -X POST "$SG_URL/api/v1/projects/$SG_PROJECT/incremental-audit" \
  -H "X-API-Key: $SG_API_KEY" -H "Content-Type: application/json" --data @payload.json
```

三个前提，答辩时要讲清楚：

1. 仓库需要先以 zip 上传一次，拿到 `project_id`；
2. runner 必须能访问服务（GitHub 托管 runner 访问不到本机，用 self-hosted）；
3. 服务端不拉取仓库、不执行 git，只接收 diff——这是有意的边界，避免把凭据和执行环境引进来。

---

## 5. 能声明什么 / 不能声明什么

**能**：在真实运行中，一次只改一个函数的提交，审计量从 8 个函数降到 1 个，未审函数在账本与报告中可见；两次运行的 finding 变化可对比。

**不能**：

| 不能声称 | 原因 |
|---|---|
| "增量审计不会漏" | 改 A 破坏 B 的情况下，B 不在 diff 里，不会被审——这是本质风险，当前无法检测 |
| "节省 87.5% 是普遍值" | 本项目 8→1 是单函数改动；多函数提交时比例会下降 |
| "影响面分析完成" | 只有同文件上下文；跨文件/调用图明确未做 |
| "CI 已验证" | 模板未在真实 GitHub runner 上跑过；本次 E2E 是直接调用同一接口 |

第 1 条必须写进论文"不足与展望"，否则答辩会被问穿。

---

## 6. 测试

- `tests/test_incremental.py`（9）：diff 解析、区间合并、映射、整文件回退、未知路径；
- `tests/test_audit_integrity.py`：新增 `only_units` 模式与五项恒等式；
- `tests/test_audit_compare.py`（2）：对比分类、跨项目拒绝。

全量 **179 passed**。
